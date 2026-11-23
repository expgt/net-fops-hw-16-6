#!/usr/bin/python

# Copyright: (c) 2026, Your Name <your.email@example.com>
# GNU General Public License v3.0+ (see COPYING or https://gnu.org)
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: yc_instance

short_description: Create a VM instance in Yandex Cloud using yc CLI

version_added: "1.1.0"

description:
    - Creates a virtual machine in Yandex Cloud with specified sizing and OS image using the yc CLI tool.
    - Ensures idempotency by checking if an instance with the given name already exists.

options:
    name:
        description: Name of the virtual machine.
        required: true
        type: str
    zone:
        description: Availability zone.
        required: false
        type: str
        default: ru-central1-a
    platform_id:
        description: Hardware platform ID.
        required: false
        type: str
        default: standard-v3
    cores:
        description: Number of vCPU cores.
        required: false
        type: int
        default: 2
    memory:
        description: RAM size in GB (e.g., 2, 4).
        required: false
        type: int
        default: 2
    core_fraction:
        description: Baseline core performance in percent (20, 50, 100).
        required: false
        type: int
        default: 20
    image_family:
        description: OS image family from standard-images (e.g., ubuntu-2204-lts).
        required: false
        type: str
        default: ubuntu-2204-lts
    image_folder_id:
        description: Folder ID containing the image family.
        required: false
        type: str
        default: standard-images
    disk_size:
        description: Boot disk size in GB.
        required: false
        type: int
        default: 15
    subnet_name:
        description: Name of the VPC subnet to attach the VM to.
        required: true
        type: str
    nat:
        description: Assign a public IPv4 address.
        required: false
        type: bool
        default: true
    preemptible:
        description: Create a preemptible VM instance (reduces cost, may be stopped after 24 hours).
        required: false
        type: bool
        default: false
    ssh_key_path:
        description: Path to the public SSH key file on the controller host.
        required: true
        type: str
    folder_id:
        description: Optional Yandex Cloud folder ID (uses default yc profile folder if omitted).
        required: false
        type: str

requirements:
    - yc CLI installed and configured

author:
    - Your Name (@yourGitHubHandle)
'''

EXAMPLES = r'''
- name: Create ClickHouse host in Yandex Cloud
  my_own_namespace.yandex_cloud_elk.yc_instance:
    name: clickhouse-01
    zone: ru-central1-a
    cores: 2
    memory: 4
    image_family: ubuntu-2204-lts
    disk_size: 20
    subnet_name: default-ru-central1-a
    nat: true
    preemptible: true
    ssh_key_path: ~/.ssh/id_ed25519.pub
'''

RETURN = r'''
instance_id:
    description: Yandex Cloud ID of the VM.
    type: str
    returned: always
    sample: 'fhm1234567890abcdef'
name:
    description: Name of the VM.
    type: str
    returned: always
    sample: 'clickhouse-01'
public_ip:
    description: Assigned external IPv4 address.
    type: str
    returned: always
    sample: '158.160.10.25'
private_ip:
    description: Assigned internal VPC IPv4 address.
    type: str
    returned: always
    sample: '10.128.0.12'
status:
    description: Current instance status.
    type: str
    returned: always
    sample: 'RUNNING'
'''

import json
import os
from ansible.module_utils.basic import AnsibleModule


def extract_ips(instance_data):
    """Извлекает внутренний и внешний IPv4 адреса из JSON-ответа yc CLI."""
    private_ip = ''
    public_ip = ''
    nics = instance_data.get('network_interfaces', [])
    if nics:
        primary_v4 = nics[0].get('primary_v4_address', {})
        private_ip = primary_v4.get('address', '')
        nat = primary_v4.get('one_to_one_nat', {})
        public_ip = nat.get('address', '')
    return private_ip, public_ip


def get_existing_instance(module, yc_bin, name, folder_id=None):
    """Проверяет, существует ли уже ВМ с указанным именем."""
    cmd = [yc_bin, 'compute', 'instance', 'list', '--format', 'json']
    if folder_id:
        cmd.extend(['--folder-id', folder_id])

    rc, out, err = module.run_command(cmd)
    if rc != 0:
        module.fail_json(msg=f"Failed to list YC instances: {err}")

    instances = json.loads(out) if out.strip() else []
    for inst in instances:
        if inst.get('name') == name:
            return inst
    return None


def run_module():
    module_args = dict(
        name=dict(type='str', required=True),
        zone=dict(type='str', required=False, default='ru-central1-a'),
        platform_id=dict(type='str', required=False, default='standard-v3'),
        cores=dict(type='int', required=False, default=2),
        memory=dict(type='int', required=False, default=2),
        core_fraction=dict(type='int', required=False, default=20),
        image_family=dict(type='str', required=False, default='ubuntu-2204-lts'),
        image_folder_id=dict(type='str', required=False, default='standard-images'),
        disk_size=dict(type='int', required=False, default=15),
        subnet_name=dict(type='str', required=True),
        nat=dict(type='bool', required=False, default=True),
        preemptible=dict(type='bool', required=False, default=False),
        ssh_key_path=dict(type='path', required=True),
        folder_id=dict(type='str', required=False, default=None),
    )

    result = dict(
        changed=False,
        instance_id='',
        name='',
        public_ip='',
        private_ip='',
        status=''
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    yc_bin = module.get_bin_path('yc', required=True)
    params = module.params
    result['name'] = params['name']

    # 1. Проверка идемпотентности
    existing = get_existing_instance(module, yc_bin, params['name'], params['folder_id'])
    if existing:
        private_ip, public_ip = extract_ips(existing)
        result['changed'] = False
        result['instance_id'] = existing.get('id', '')
        result['private_ip'] = private_ip
        result['public_ip'] = public_ip
        result['status'] = existing.get('status', '')
        module.exit_json(**result)

    # 2. Обработка check_mode (--check)
    if module.check_mode:
        result['changed'] = True
        result['status'] = 'CHECK_MODE_WOULD_CREATE'
        module.exit_json(**result)

    if not os.path.exists(params['ssh_key_path']):
        module.fail_json(msg=f"SSH public key not found at: {params['ssh_key_path']}", **result)

    # 3. Формирование параметров сетевого интерфейса и загрузочного диска
    net_interface = f"subnet-name={params['subnet_name']}"
    if params['nat']:
        net_interface += ",nat-ip-version=ipv4"

    boot_disk = (
        f"image-folder-id={params['image_folder_id']},"
        f"image-family={params['image_family']},"
        f"size={params['disk_size']}GB"
    )

    cmd = [
        yc_bin, 'compute', 'instance', 'create',
        '--name', params['name'],
        '--zone', params['zone'],
        '--platform', params['platform_id'],
        '--cores', str(params['cores']),
        '--memory', f"{params['memory']}GB",
        '--core-fraction', str(params['core_fraction']),
        '--network-interface', net_interface,
        '--create-boot-disk', boot_disk,
        '--ssh-key', params['ssh_key_path'],
        '--format', 'json'
    ]

    if params['preemptible']:
        cmd.append('--preemptible')

    if params['folder_id']:
        cmd.extend(['--folder-id', params['folder_id']])

    rc, out, err = module.run_command(cmd)
    if rc != 0:
        module.fail_json(msg=f"Failed to create VM '{params['name']}': {err}", **result)

    created = json.loads(out)
    private_ip, public_ip = extract_ips(created)

    result['changed'] = True
    result['instance_id'] = created.get('id', '')
    result['private_ip'] = private_ip
    result['public_ip'] = public_ip
    result['status'] = created.get('status', 'RUNNING')

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
