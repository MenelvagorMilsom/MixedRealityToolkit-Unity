import sys
from ruamel import yaml

def file_id_to_int(file_id):
    split_id = file_id.split('_')
    return int(split_id[1])

# converts fileID string to dictionary
def file_id_to_dict(file_id):
    return {'fileID': file_id_to_int(file_id)}


# converts fileID dictionary to string
def dict_to_file_id(id_dict):
    return 'fileID_' + str(id_dict['fileID'])


# returns null fileID ({fileID: 0})
def null_id():
    return {'fileID': 0}

    
# returns the maximum fileID in a doc
def find_max_id(doc):
    max_id = 0
    for file_id, _ in doc:
        int_id = file_id_to_int(file_id)
        max_id = max(int_id, max_id)
    
    return max_id
    

# Tags cause issues with yaml parsing as .unity files are not
# correctly formed.
def remove_tags(file_path):
    result = str()
    with open(file_path, 'r') as source_file:
        for _, line in enumerate(source_file.readlines()):
            if line.startswith('--- !u!'):
                # Remove the tag and new doc, create object called fileID_<fileID>
                # store tag string to reconstruct document later
                split_anchor = line.split(' ') 
                result += 'fileID_' + split_anchor[2][1:].strip() + ':\n'
                result += '  tag: "' + split_anchor[1].strip() + '"\n'
                result += '  stripped: "' + (split_anchor[3] if len(split_anchor) == 4 else '').strip() + '"\n'
            elif line.startswith('%'):
                # Remove the Unity tag line and add top level doc after
                # yaml version no.
                if not line.startswith('%TAG !u! tag:unity3d.com,2011:'):
                    result += line + '---\n'
            else:
                # Just copy the contents, indent as we've added top level
                # objects rather than separate documents
                result += '  ' + line
    
    return result


def dump_unity_file(doc, file_path):
    with open (file_path, 'w') as dest_file:
        dest_file.write('%YAML 1.1\n')
        dest_file.write('%TAG !u! tag:unity3d.com,2011:\n')

        for file_id, fields in doc.items():
            dest_file.write('--- {} &{} {}'.format(fields['tag'], file_id_to_int(file_id), fields['stripped']).strip() + '\n')
            del(fields['tag'])
            del(fields['stripped'])
            dest_file.write(yaml.dump(fields, Dumper=yaml.RoundTripDumper))


def progress(count, total, status=''):
    bar_len = 60
    filled_len = int(round(bar_len * count / float(total)))

    percents = round(100.0 * count / float(total), 1)
    bar = '=' * filled_len + '-' * (bar_len - filled_len)

    sys.stdout.write('[%s] %s%s ...%s\r' % (bar, percents, '%', status))
    if count == total:
        sys.stdout.write('\n')
    sys.stdout.flush()