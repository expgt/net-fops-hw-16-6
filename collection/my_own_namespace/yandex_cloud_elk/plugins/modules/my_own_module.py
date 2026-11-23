#!/usr/bin/python

# Copyright: (c) 2026, Your Name <your.email@example.org>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: my_own_module

short_description: Create a text file on a remote host

version_added: "1.0.0"

description: This module creates a text file at the specified path with the given content.

options:
    path:
        description: Path to the file to be created on the remote host.
        required: true
        type: path
    content:
        description: Content to write into the file.
        required: true
        type: str

author:
    - AleksandrR
'''

EXAMPLES = r'''
# Create a file with specific content
- name: Create test file
  my_own_namespace.yandex_cloud_elk.my_own_module:
    path: /tmp/test_file.txt
    content: "Hello, Ansible!"
'''

RETURN = r'''
path:
    description: Path to the created or modified file.
    type: str
    returned: always
    sample: '/tmp/test_file.txt'
message:
    description: Status message describing the action taken.
    type: str
    returned: always
    sample: 'File created or updated successfully'
'''

import os
from ansible.module_utils.basic import AnsibleModule


def run_module():
    module_args = dict(
        path=dict(type='path', required=True),
        content=dict(type='str', required=True)
    )

    result = dict(
        changed=False,
        path='',
        message=''
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    file_path = module.params['path']
    new_content = module.params['content']
    result['path'] = file_path

    file_exists = os.path.exists(file_path)
    current_content = None

    if file_exists:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                current_content = f.read()
        except Exception as e:
            module.fail_json(msg=f"Failed to read existing file: {e}", **result)

    if not file_exists or current_content != new_content:
        result['changed'] = True
        result['message'] = 'File created or updated successfully'
    else:
        result['changed'] = False
        result['message'] = 'File already exists with the requested content'

    if module.check_mode:
        module.exit_json(**result)

    if result['changed']:
        try:
            parent_dir = os.path.dirname(file_path)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
        except Exception as e:
            module.fail_json(msg=f"Failed to write file: {e}", **result)

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
