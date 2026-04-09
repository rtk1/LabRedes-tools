"""
Retrieves YANG schemas from a Huawei NETCONF device.

This script connects to a Huawei NETCONF device, retrieves its capabilities,
and fetches the YANG schema for each capability that specifies a module.
Schemas are saved to files in the specified output directory.

Usage:
    python get_schemas_from_caps.py <host> <username> <password> [output_directory]
"""

import sys
import os
import argparse  
import re
from ncclient import manager
from xml.etree import ElementTree as ET

def _extract_module_name(capability_uri):
    """
    Extracts the module name from a capability URI using regex.
    
    Args:
        capability_uri (str): The capability URI to parse
            Example: "urn:ietf:params:xml:ns:yang:ietf-yang-types?module=ietf-yang-types&revision=2013-07-15"
    
    Returns:
        str | None: The module name if found (e.g. "ietf-yang-types"), None if no module found
    """
    if "?" not in capability_uri:
        return None
    query = capability_uri.split("?", 1)[1]
    match = re.search(r"module=([^&]*)", query)
    return match.group(1) if match else None

def _retrieve_schema(netconf_manager, module_name):
    """Retrieves a YANG schema using get-schema.

    Args:
        netconf_manager: An active ncclient manager instance.
        module_name:     The name of the module to retrieve.

    Returns:
        The schema as a string, or None on error.  Returns an empty
        string if the schema is empty.
    """
    try:
        reply = netconf_manager.get_schema(module_name, format="yang")
        return reply.data_ele or ''  # Handle potentially empty schema
    except Exception as e:
        print(f"Error retrieving schema for {module_name}: {e}", file=sys.stderr)
        return None

def _save_schema(output_dir, module_name, schema_data):
    """Saves the schema data to a file.

    Args:
        output_dir:   The directory to save the schema in.
        module_name:  The name of the module (used for filename).
        schema_data: The schema content (string).
    """
    filename = os.path.join(output_dir, f"{module_name}.yang")
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(schema_data)
        print(f"Schema saved to {filename}")
    except OSError as e:
        print(f"Error saving schema to {filename}: {e}", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(description="Retrieve YANG schemas from a Huawei NETCONF device.")
    parser.add_argument("host", help="The device hostname or IP address")
    parser.add_argument("username", help="The NETCONF username")
    parser.add_argument("password", help="The NETCONF password")
    parser.add_argument("output_dir", nargs='?', default="huawei-schema",
                        help="The output directory (default: huawei-schema)")
    args = parser.parse_args()

    # Create output directory if it doesn't exist
    try:
        os.makedirs(args.output_dir, exist_ok=True)
    except OSError as e:
        print(f"Error creating output directory {args.output_dir}: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        with manager.connect(host=args.host, port=830, username=args.username,
                             password=args.password, hostkey_verify=False,
                             device_params={'name': 'huaweiyang'},
                             timeout=60) as m:

            for capability in m.server_capabilities:
                module_name = _extract_module_name(capability)
                if module_name:
                    print(f"Retrieving schema for module: {module_name}")
                    schema = _retrieve_schema(m, module_name)
                    if schema is not None:
                        _save_schema(args.output_dir, module_name, schema)

    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()