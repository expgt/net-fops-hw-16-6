# Ansible Collection - my_own_namespace.yandex_cloud_elk

Коллекция содержит пользовательский модуль `my_own_module` и роль `my_own_role` для создания текстовых файлов на целевых хостах.

## Состав коллекции

### Модули
* `my_own_namespace.yandex_cloud_elk.my_own_module` — создаёт текстовый файл по указанному пути `path` с содержимым `content`. Поддерживает идемпотентность и режим `--check`.

### Роли
* `my_own_namespace.yandex_cloud_elk.my_own_role` — вызывает модуль `my_own_module` с использованием переменных по умолчанию (`path: /tmp/default_role_file.txt`, `content: "Default content from my_own_role!"`).

## Пример использования

```yaml
---
- name: Run my_own_role from collection
  hosts: localhost
  connection: local
  gather_facts: false
  roles:
    - role: my_own_namespace.yandex_cloud_elk.my_own_role
      vars:
        path: /tmp/test_file.txt
        content: "Hello from collection!"
```
