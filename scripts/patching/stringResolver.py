from pathlib import Path
import re
from ruamel import yaml

from patchHelpers import *

# This class is used to resolve the value strings from patch yamls.
# The syntax to reference existing values in an asset is as follows:
# - A value can be a raw value or reference string. Reference strings
#   are marked with quotations and triple curly braces.
# - Reference strings read a chain of fields from left to right,
#   delimited by double colons.
# - All fields should be given as they appear in Unity asset files
# - Subsequent fields in the chain can be:
#   a) fields of the previous field object
#   b) a component type if the previous object was a fileID pointing
#      to a component of that type
#   c) 'GameObject' or a component type if the previous object was a
#      fileID pointing to a GameObject
#   d) an index string if the previous object was an array
# - If the current object is the null fileID ({fileID: 0}), this function
#   will return the default value.
#
# Examples:
# - value: 101
# - value: 'HelloPatch'
# - value: '{{{ GameObject::m_Name }}}'
# - value: '{{{ Transform::m_LocalScale::x }}}'
# - value: '{{{ MonoBehaviour<BoundingBox>::targetObject::Transform::m_LocalScale::x }}}'
# - value: '{{{ MonoBehaviour<SomeComponent>::someVecArray::[1]::y }}}'
class StringResolver:
    def __init__(self, prefabs_dir):
        self.prefabs = {}
        for file_name in Path(prefabs_dir).glob('**/*.prefab.meta'):
            prefab_meta = yaml.load(open(file_name, 'r'), Loader=yaml.RoundTripLoader)
            self.prefabs[prefab_meta['guid']] = str(file_name).strip('.meta')
        self.doc = {}
        self.patch = {}


    def set_current_doc(self, doc):
        self.doc = doc


    def set_current_patch(self, patch):
        self.patch = patch


    def resolve_value(self, current_id, value, default):
        value_string = str(value)
        # early out if not reference string
        if not value_string.startswith('{{{') and not value_string.endswith('}}}'):
            return value

        # get the links
        value_string = value_string[3:-3]
        value_string = value_string.strip()
        value_chain = value_string.split('::')

        # set starting variables for search
        curr = self.doc[current_id]
        prev_link = ''

        for value_link in value_chain:
            # variables to aid search
            last = value_link == value_chain[-1]
            prev = curr

            # for dicts, use link string to continue search
            if type(curr) is dict:
                # link may contain component type if it is a MonoBehaviour
                split_link = re.findall(r'^(\w+)(<\w+>)?$', value_link)[0]
                link = split_link[0]
                component_type = ''
                if split_link[1] != '':
                    component_type = split_link[1][1:-1]

                if link == '':
                    raise KeyError('Failed to resolve value string, {} is not a valid field name'.format(value_link))

                if 'fileID' in curr and link not in curr:
                    if curr == null_id():
                        return default
                    
                    # found link to new object
                    current_id = dict_to_file_id(curr)
                    curr = self.doc[current_id]

                    if link in curr and last:
                        # if top level and last, return fileID object, no need to continue searching
                        curr = file_id_to_dict(current_id)
                        continue

                if link in curr:
                    # normal following the links down through an object
                    curr = curr[link]

                elif 'GameObject' in curr:
                    # search through components of current object as link was not found
                    if 'm_Component' in curr['GameObject']:
                        # not a prefab
                        for component in curr['GameObject']['m_Component']:
                            component_id = dict_to_file_id(component['component'])
                            component_obj = self.doc[component_id]
                            if link in component_obj:
                                if component_type != '':
                                    # additional information given to find component
                                    if component_obj[link]['m_Script']['guid'] != self.patch['components'][component_type]:
                                        continue
                                if last:
                                    # last, so set to fileID object
                                    curr = component['component']
                                else:
                                    # set curr to component object and continue search
                                    curr = component_obj[link]

                                current_id = component_id
                                break

                    elif ('m_PrefabInstance' in curr['GameObject'] and
                            curr['GameObject']['m_PrefabInstance'] != null_id()):
                        # GameObject is prefab, do prefab search
                        if curr['GameObject']['m_PrefabInstance']['m_CorrespondingSourceObject']['guid'] != self.prefabs:
                            print('Not implemented')
                            return {}

                        curr = self.prefab_search(curr['GameObject'], link)

                    else:
                        # Some prefab GameObjects have no component list, but still have components
                        # in the doc. We search the whole doc for components that belong to
                        # the current GameObject.
                        for file_id, obj in self.doc.items():
                            if (link in obj and
                                'm_GameObject' in obj[link] and
                                dict_to_file_id(obj[link]['m_GameObject']) == current_id):
                                if component_type != '':
                                    # additional information given to find component
                                    if obj[link]['m_Script']['guid'] != self.patch['components'][component_type]:
                                        continue
                                if last:
                                    # last, so set to fileID object
                                    curr = file_id_to_dict(file_id)
                                else:
                                    # set curr to component object and continue search
                                    curr = obj[link]

                                current_id = file_id
                                break

                elif 'm_PrefabInstance' in curr and curr['m_PrefabInstance'] != null_id():
                    # curr is a prefab instance
                    curr = self.prefab_search(curr, link)

            elif type(curr) is list:
                # should find index string
                split_link = re.findall(r'^\[(\d+)\]$', value_link)[0]
                split_link[0]

                if split_link[0] == '':
                    raise IndexError('Failed to resolve value string, {} is not a valid index name'.format(value_link))

                index = int(split_link[0])

                if index < len(curr):
                    curr = curr[index]
                else:
                    raise IndexError('Failed to resolve value string, index {} out of range of {} array'.format(index, prev_link))

            # no change
            if curr == prev:
                raise KeyError('Failed to resolve value string, could not find value of {} in {} for fileID {}'.format(value_link, prev_link, current_id))

            prev_link = value_link

        return curr


    def prefab_search(self, curr, link):
        print("Prefab Search")
        prefab_instance_id = dict_to_file_id(curr['m_PrefabInstance'])
        prefab_file_id = dict_to_file_id(curr['m_CorrespondingSourceObject'])
        prefab_instance = self.doc[prefab_instance_id]['PrefabInstance']
        prefab_guid = prefab_instance['m_SourcePrefab']['guid']
        prefab_file = self.prefabs[prefab_guid]
        prefab_doc = yaml.load(remove_tags(prefab_file), Loader=yaml.RoundTripLoader)

        if prefab_file_id in prefab_doc and link in prefab_doc[prefab_file_id]:
            return prefab_doc[prefab_file_id][link]
        else:
            raise KeyError('Failed to resolve value string, could not find value of {} in {} for the prefab {}'.format(link, prefab_file_id, prefab_file))
