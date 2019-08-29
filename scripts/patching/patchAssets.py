import argparse
import copy
from itertools import chain
from os import path as os_path
from pathlib import Path
try:
    from pip import main as pipmain
except:
    from pip._internal import main as pipmain
from pkg_resources import parse_version
import re

# ensure we have ruamel.yaml
pipmain(['install', 'ruamel.yaml'])
from ruamel import yaml

from patchHelpers import *
from stringResolver import StringResolver

class UnityPatcher:
    def __init__(self, assets_dir):
        self.string_resolver = StringResolver(assets_dir)


    def check_component_conditions(self, doc, patch, conditions, object_id):
        if 'has' in conditions:
            for item in conditions['has']:
                script_guid = patch['components'][item]
                found = False
                for component in doc[object_id]['GameObject']['m_Component']:
                    component_id = dict_to_file_id(component['component'])
                    if ('MonoBehaviour' in doc[component_id] and 
                       doc[component_id]['MonoBehaviour']['m_Script']['guid'] == script_guid):
                        found = True

                if not found:
                    return False

        if 'doesNotHave' in conditions:
            for item in conditions['doesNotHave']:
                script_guid = patch['components'][item]
                found = False
                for component in doc[object_id]['GameObject']['m_Component']:
                    component_id = dict_to_file_id(component['component'])
                    if ('MonoBehaviour' in doc[component_id] and 
                       doc[component_id]['MonoBehaviour']['m_Script']['guid'] == script_guid):
                        found = True

                if found:
                    return False

        return True


    def check_value_conditions(self, conditions, component, field_name):
        if 'equals' in conditions:
            if component[field_name] != conditions['equals']:
                return False

        if 'notEquals' in conditions:
            if component[field_name] == conditions['equals']:
                return False

        return True


    def add_field(self, doc, new_doc, patch):
        for field_patch in patch['actions']['addField']:
            # get script guid of components to modify
            script_guid = patch['components'][field_patch['component']]

            # find all MonoBehaviours with the given guid
            for file_id, fields in doc.items():
                if 'MonoBehaviour' not in fields:
                    continue

                component = fields['MonoBehaviour']
                object_id = dict_to_file_id(component['m_GameObject'])

                if component['m_Script']['guid'] != script_guid:
                    continue

                if ('conditions' in field_patch and
                    not self.check_component_conditions(doc, patch, field_patch['conditions'], object_id)):
                    continue

                # all conditions met, add field
                default = default = field_patch['default'] if 'default' in field_patch else ''
                value = self.string_resolver.resolve_value(object_id, field_patch['value'], default)
                new_doc[file_id]['MonoBehaviour'][field_patch['name']] = value


    def delete_field(self, doc, new_doc, patch):
        for field_patch in patch['actions']['deleteField']:
            # get script guid of components to modify
            script_guid = patch['components'][field_patch['component']]

            # find all MonoBehaviours with the given guid
            for file_id, fields in doc.items():
                if 'MonoBehaviour' not in fields:
                    continue

                component = fields['MonoBehaviour']
                object_id = dict_to_file_id(component['m_GameObject'])
                field_name = field_patch['name']

                if component['m_Script']['guid'] != script_guid:
                    continue

                if ('conditions' in field_patch and
                    (not self.check_component_conditions(doc, patch, field_patch['conditions'], object_id) or
                    not self.check_value_conditions(field_patch['conditions'], component, field_name))):
                    continue

                # all conditions met, delete field
                del(new_doc[file_id]['MonoBehaviour'][field_name])


    def rename_field(self, doc, new_doc, patch):
        for field_patch in patch['actions']['renameField']:
            # get script guid of components to modify
            script_guid = patch['components'][field_patch['component']]

            # find all MonoBehaviours with the given guid
            for file_id, fields in doc.items():
                if 'MonoBehaviour' not in fields:
                    continue

                component = fields['MonoBehaviour']
                object_id = dict_to_file_id(component['m_GameObject'])
                field_name = field_patch['name']

                if component['m_Script']['guid'] != script_guid:
                    continue

                if ('conditions' in field_patch and
                    not self.check_component_conditions(doc, patch, field_patch['conditions'], object_id)):
                    continue

                # all conditions met, create new name field and delete old field
                new_doc[file_id]['MonoBehaviour'][field_patch['newName']] = component[field_name]
                del(new_doc[file_id]['MonoBehaviour'][field_name])


    def modify_field(self, doc, new_doc, patch):
        for field_patch in patch['actions']['modifyField']:
            # get script guid of components to modify
            script_guid = patch['components'][field_patch['component']]

            # find all MonoBehaviours with the given guid
            for file_id, fields in doc.items():
                if 'MonoBehaviour' not in fields:
                    continue

                component = fields['MonoBehaviour']
                object_id = dict_to_file_id(component['m_GameObject'])
                field_name = field_patch['name']

                if component['m_Script']['guid'] != script_guid:
                    continue

                if ('conditions' in field_patch and
                    (not self.check_component_conditions(doc, patch, field_patch['conditions'], object_id) or
                    not self.check_value_conditions(field_patch['conditions'], component, field_name))):
                    continue

                # all conditions met, delete field
                default = default = field_patch['default'] if 'default' in field_patch else ''
                value = self.string_resolver.resolve_value(object_id, field_patch['newValue'], default)
                new_doc[file_id]['MonoBehaviour'][field_name] = value


    def add_component(self, doc, new_doc, patch):
        for component_patch in patch['actions']['addComponent']:
            # find all GameObjects that satisfy given conditions
            for file_id, fields in doc.items():
                if 'GameObject' not in fields or 'm_Component' not in fields['GameObject']:
                    continue

                if ('conditions' in component_patch and
                    not self.check_component_conditions(doc, patch, component_patch['conditions'], file_id)):
                    continue

                new_obj = {'MonoBehaviour': {}}

                # add unity fields
                unity_fields = component_patch['component']['unityFields']
                new_obj['MonoBehaviour']['m_ObjectHideFlags'] = (
                    unity_fields['m_ObjectHideFlags'] 
                    if 'm_ObjectHideFlags' in unity_fields 
                    else 0
                )
                new_obj['MonoBehaviour']['m_CorrespondingSourceObject'] = (
                    unity_fields['m_CorrespondingSourceObject'] 
                    if 'm_CorrespondingSourceObject' in unity_fields 
                    else null_id()
                )
                new_obj['MonoBehaviour']['m_PrefabInstance'] = (
                    unity_fields['m_PrefabInstance'] 
                    if 'm_PrefabInstance' in unity_fields 
                    else null_id()
                )
                new_obj['MonoBehaviour']['m_PrefabAsset'] = (
                    unity_fields['m_PrefabAsset'] 
                    if 'm_ObjectHideFlags' in unity_fields 
                    else null_id()
                )
                new_obj['MonoBehaviour']['m_Enabled'] = (
                    unity_fields['m_Enabled'] 
                    if 'm_Enabled' in unity_fields 
                    else 1
                )
                new_obj['MonoBehaviour']['m_EditorHideFlags'] = (
                    unity_fields['m_EditorHideFlags'] 
                    if 'm_EditorHideFlags' in unity_fields
                    else 0
                )
                new_obj['MonoBehaviour']['m_Name'] = (
                    unity_fields['m_Name'] 
                    if 'm_Name' in unity_fields
                    else ''
                )
                new_obj['MonoBehaviour']['m_EditorClassIdentifier'] = (
                    unity_fields['m_EditorClassIdentifier'] 
                    if 'm_EditorClassIdentifier' in unity_fields
                    else ''
                )

                new_obj['MonoBehaviour']['m_GameObject'] = file_id_to_dict(file_id)
                new_obj['MonoBehaviour']['m_Script'] = {
                    'fileID': 11500000,
                    'guid': patch['components'][component_patch['component']['type']],
                    'type': 3
                }

                # add fields belonging to new MonoBehaviour
                for component_field in component_patch['component']['componentFields']:
                    default = component_field['default'] if 'default' in component_field else ''
                    value = self.string_resolver.resolve_value(file_id, component_field['value'], default)
                    new_obj['MonoBehaviour'][component_field['name']] = value

                # create new fileID and add object to document
                max_id = find_max_id(doc)
                max_id += 1
                new_id = 'fileID_' + str(max_id)
                new_id_dict = file_id_to_dict(new_id)

                new_doc[new_id] = new_obj
                new_doc[file_id]['m_Component'].append({'component': new_id_dict})


    def delete_component(self, doc, new_doc, patch):
        for component_patch in patch['actions']['addComponent']:
            # find all GameObjects that satisfy given conditions
            for file_id, fields in doc.items():
                if 'GameObject' not in fields or 'm_Component' not in fields['GameObject']:
                    continue

                if ('conditions' in component_patch and
                    not self.check_component_conditions(doc, patch, component_patch['conditions'], file_id)):
                    continue

                script_guid = patch['components'][component_patch['type']]

                for component in fields['m_Component']:                    
                    component_id = dict_to_file_id(component['component'])
                    if doc[component_id]['MonoBehaviour']['m_Script']['guid'] == script_guid:
                        del(new_doc[component_id])
                        new_doc[file_id]['m_Component'].remove(component)


    def patch_document(self, doc, new_doc, patch):
        self.string_resolver.set_current_doc(doc)
        self.string_resolver.set_current_patch(patch)

        new_doc = copy.deepcopy(doc)

        if len(patch['actions']['addField']) > 0:
            self.add_field(doc, new_doc, patch)
        if len(patch['actions']['deleteField']) > 0:
            self.delete_field(doc, new_doc, patch)
        if len(patch['actions']['renameField']) > 0:
            self.rename_field(doc, new_doc, patch)
        if len(patch['actions']['modifyField']) > 0:
            self.modify_field(doc, new_doc, patch)
        if len(patch['actions']['addComponent']) > 0:
            self.add_component(doc, new_doc, patch)
        if len(patch['actions']['deleteComponent']) > 0:
            self.delete_component(doc, new_doc, patch)

        return new_doc


    def patch_documents(self, from_version, to_version, assets_dir, patches_dir):
        # iterate over
        files = list(chain(
            Path(assets_dir).glob('**/*.unity'), 
            Path(assets_dir).glob('**/*.prefab'), 
            Path(assets_dir).glob('**/*.asset')
        ))
        
        count = 0
        for file_path in files:
            doc = yaml.load(remove_tags(file_path), Loader=yaml.RoundTripLoader)
            new_doc = copy.deepcopy(doc)

            for yaml_name in Path(patches_dir).glob('**/*.yml'):
                for patch in yaml.load_all(open(yaml_name, 'r'), Loader=yaml.RoundTripLoader):
                    self.patch_document(doc, new_doc, patch)
            
            dump_unity_file(new_doc, file_path)
            count += 1
            progress(count, len(files))      


if __name__ == '__main__':
    # parse command line options
    parser = argparse.ArgumentParser(description='Patch Unity documents')
    parser.add_argument('from_version', type=str, help='Old package version to update from')
    parser.add_argument('to_version', type=str, help='New package version to update to')
    parser.add_argument('assets_dir', type=str, help='Path to unity project assets directory')
    parser.add_argument('patches_dir', type=str, help='Path to patch files directory')
    args = parser.parse_args()
    
    assert parse_version(args.from_version) < parse_version(args.to_version), 'from_version must be less than to_version'
    assert os_path.isdir(args.assets_dir), 'assets_dir is not a valid path'
    assert os_path.isdir(args.patches_dir), 'patches_dir is not a valid path'

    # create patcher and run patches
    patcher = UnityPatcher(args.assets_dir)
    patcher.patch_documents(args.from_version, args.to_version, args.assets_dir, args.patches_dir)