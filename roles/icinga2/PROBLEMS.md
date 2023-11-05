 
```
An exception occurred during task execution. To see the full traceback, use -vvv. The error was: BlockingIOError: [Errno 11] Resource temporarily unavailable
failed: [app1.stage.otc.closed.com -> icinga2-master] (item={'key': 'icinga2-master', 'value': {'ip': '192.168.2.24'}}) => changed=false 
  ansible_loop_var: item
  item:
    key: icinga2-master
    value:
      ip: 192.168.2.24
  module_stderr: |-
    Traceback (most recent call last):
      File "<stdin>", line 100, in <module>
      File "<stdin>", line 92, in _ansiballz_main
      File "<stdin>", line 40, in invoke_module
      File "/usr/lib/python3.9/runpy.py", line 210, in run_module
        return _run_module_code(code, init_globals, run_name, mod_spec)
      File "/usr/lib/python3.9/runpy.py", line 97, in _run_module_code
        _run_code(code, mod_globals, init_globals,
      File "/usr/lib/python3.9/runpy.py", line 87, in _run_code
        exec(code, run_globals)
      File "/tmp/ansible_icinga2_reload_master_payload_58zehmnc/ansible_icinga2_reload_master_payload.zip/ansible/modules/icinga2_reload_master.py", line 171, in <module>
      File "/tmp/ansible_icinga2_reload_master_payload_58zehmnc/ansible_icinga2_reload_master_payload.zip/ansible/modules/icinga2_reload_master.py", line 162, in main
      File "/tmp/ansible_icinga2_reload_master_payload_58zehmnc/ansible_icinga2_reload_master_payload.zip/ansible/modules/icinga2_reload_master.py", line 93, in run
      File "/tmp/ansible_icinga2_reload_master_payload_58zehmnc/ansible_icinga2_reload_master_payload.zip/ansible/modules/icinga2_reload_master.py", line 36, in __enter__
    BlockingIOError: [Errno 11] Resource temporarily unavailable
  module_stdout: ''
  msg: |-
    MODULE FAILURE
    See stdout/stderr for the exact error
  rc: 1

```


- name: create icinga2 constants.conf
  icinga2_constants:
    icinga2_version: "2.13.7"
    icinga2_master: "{{ icinga2_primary_master }}"
    icinga2_mode: "{{ icinga2_mode }}"
    constants:
      PluginDir: "{{ monitoring_plugins_directory }}"
      NodeName: "{{ icinga2_certificate_cn }}"
      ZoneName: "{{ ansible_fqdn }}"
      TicketSalt: "{{ icinga2_salt }}"
    owner: "{{ icinga2_user | default('icinga2') }}"
    group: "{{ icinga2_group | default('icinga2') }}"

  notify:
    - check configuration
    - restart icinga2
