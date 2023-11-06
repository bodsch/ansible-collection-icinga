# python 3 headers, required if submitting to Ansible
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from ansible.utils.display import Display
import os

display = Display()


class FilterModule(object):
    """
    """
    def filters(self):
        return {
            'installed_modules': self.installed_modules,
        }

    def installed_modules(self, data):
        """
        """
        _data = data.copy()
        if isinstance(data, dict):
            for t, v in _data.items():
                # display.v(f"  - {t}")
                # display.v(f"    {v}")
                if v.get("download", None):
                    _ = v.pop("download")
                if v.get("src", None):
                    _ = v.pop("src")

        # display.v(f"result : {_data}")

        return _data
