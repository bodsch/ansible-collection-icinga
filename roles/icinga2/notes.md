
primary.conf.j2

{#
    {% if icinga2_masters | bodsch.core.type == "dict" %}
      {% set ip = icinga2_masters.get(endpoint_name, {}).get("ip", None) %}
      {% if ip %}
        {# use defined IP address #}
        {% set address = ip %}
      {% else %}
{#
  use you *functional* dns to resolve hostname.
  this runs on the ansible-host and not on the destination machine!
#}
/*
  Use the DNS resolver on the Ansible controller.
        {% if endpoint_name %}
          {# try the endpoint_name #}
          {% set dns_data = endpoint_name | bodsch.core.dns_lookup() %}
          {% set dns_error = dns_data.get("error", False) %}
          {% set dns_addrs = dns_data.get("addrs", []) %}
          {% if not dns_error and dns_addrs | count > 0 %}
            {% if dns_addrs | count > 1 %}
  multiple IPs for endpoint_name {{ endpoint_name }} defined: {{ dns_addrs }}
{#
  multiple DNS entries are a problem!
  you should configure 'icinga2_satellites' properly
#}
            {% endif %}
            {% set address = dns_addrs[0] %}
          {% endif %}
        {% endif %}
        {# try the ansible_fqdn #}
        {% set dns_data = ansible_fqdn | bodsch.core.dns_lookup() %}
        {% set dns_error = dns_data.get("error", False) %}
        {% set dns_addrs = dns_data.get("addrs", []) %}
        {% if not dns_error and dns_addrs | count > 0 %}
          {% if dns_addrs | count > 1 %}
{#
  multiple DNS entries are a problem!
  you should configure 'icinga2_satellites' properly
#}
// multiple IPs defined: {{ dns_addrs }}
          {% endif %}
          {% set address = dns_addrs[0] %}
        {% endif %}
        {# finaly .. use the ansible_fqdn and hope the best #}
        {# endpoint definition final #}
      {% endif %}
    {% endif %}
#} 

satellie.conf.j2

    {% set ip = "" %}
    {% set satellite_ip = "" %}
    {% if address is defined and address | string | length > 0 %}
      {% set satellite_ip = address %}
    {% else %}
      {% if icinga2_satellites | bodsch.core.type == "dict" %}
        {% set ip = icinga2_satellites.get(icinga2_satellite_zone, {}).get(object_name, {}).get("ip", None) %}
      {% endif %}
      {% if ip %}
        {% set satellite_ip = ip %}
      {% else %}
        {#
          use local dns resolver
        #}
        {% set dns_data = ansible_fqdn | bodsch.core.dns_lookup() %}
        {% set dns_error = dns_data.get("error", False) %}
        {% set dns_addrs = dns_data.get("addrs", []) %}
        {% if not dns_error and dns_addrs | count > 0 %}
          {% if dns_addrs | count > 1 %}
{#
  multiple DNS entries are a problem!
  you should configure 'icinga2_satellites' properly
#}
// multiple IPs defined: {{ dns_addrs }}
          {% endif %}
          {% set satellite_ip = dns_addrs[0] %}
        {% endif %}
        {# endpoint definition final #}
      {% endif %}
    {% endif %}
    
----    
