"""
Retrieves YANG schemas from a Cisco NETCONF device (e.g., IOS XR, IOS XE, NX-OS).

This script connects to a Cisco NETCONF device, retrieves its capabilities,
and fetches the YANG schema for each capability that specifies a module.
Schemas are saved to files in the specified output directory.

Usage:
    python cisco_get_schema.py <host> <username> <password> [output_directory]
"""

import sys
import os
import argparse
import re
from ncclient import manager
from xml.etree import ElementTree as ET


def _extract_module_and_revision(capability_uri: str):
    """Extract module name and revision from a capability URI.

    Example of capability:
    "urn:ietf:params:xml:ns:yang:ietf-interfaces?module=ietf-interfaces&revision=2018-02-20"

    Returns:
        (module: str | None, revision: str | None)
    """
    if "?" not in capability_uri:
        return None, None
    query = capability_uri.split("?", 1)[1]
    m_mod = re.search(r"(?:^|&)module=([^&]*)", query)
    m_rev = re.search(r"(?:^|&)revision=([^&]*)", query)
    module = m_mod.group(1) if m_mod else None
    revision = m_rev.group(1) if m_rev else None
    return module, revision


def _retrieve_schema(netconf_manager, module_name: str, revision: str | None):
    """Retrieve a YANG schema using get-schema.

    Tries to use `version` when provided, falls back to module-only.

    Returns the schema as a string, or None on error.
    """
    try:
        if revision:
            reply = netconf_manager.get_schema(module_name, version=revision, format="yang")
        else:
            reply = netconf_manager.get_schema(module_name, format="yang")

        # ncclient usually exposes `data` containing the YANG text
        schema_text = getattr(reply, "data", None)
        if isinstance(schema_text, bytes):
            schema_text = schema_text.decode("utf-8", errors="replace")

        if not schema_text:
            # Fallback: parse from XML
            try:
                root = ET.fromstring(getattr(reply, "xml", ""))
                ns = {"nc": "urn:ietf:params:xml:ns:netconf:base:1.0"}
                data_elem = root.find("nc:data", ns)
                if data_elem is not None and data_elem.text is not None:
                    schema_text = data_elem.text
            except Exception:
                pass

        return schema_text if schema_text is not None else ""

    except Exception as e:
        print(f"Error retrieving schema for {module_name}{'@'+revision if revision else ''}: {e}", file=sys.stderr)
        return None


def _save_schema(output_dir: str, module_name: str, revision: str | None, schema_data: str):
    """Save the schema to a file. Include revision in filename when available."""
    suffix = f"@{revision}" if revision else ""
    filename = os.path.join(output_dir, f"{module_name}{suffix}.yang")
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(schema_data)
        print(f"Schema saved to {filename}")
    except OSError as e:
        print(f"Error saving schema to {filename}: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Retrieve YANG schemas from a Cisco NETCONF device.")
    parser.add_argument("host", help="The device hostname or IP address")
    parser.add_argument("username", help="The NETCONF username")
    parser.add_argument("password", help="The NETCONF password")
    parser.add_argument("output_dir", nargs='?', default="cisco-schema",
                        help="The output directory (default: cisco-schema)")
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
                             device_params={'name': 'iosxr'},
                             timeout=60) as m:

            seen = set()
            for capability in m.server_capabilities:
                module_name, revision = _extract_module_and_revision(capability)
                if not module_name:
                    continue
                key = (module_name, revision)
                if key in seen:
                    continue
                seen.add(key)

                print(f"Retrieving schema for module: {module_name}{'@'+revision if revision else ''}")
                schema = _retrieve_schema(m, module_name, revision)
                if schema is not None:
                    _save_schema(args.output_dir, module_name, revision, schema)

    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
"""
Retrieves YANG schemas from a Cisco NETCONF device (IOS XR/IOS XE/NX-OS).

This script connects to a Cisco NETCONF device, retrieves its capabilities,
and fetches the YANG schema for each capability that specifies a module.
Schemas are saved to files in the specified output directory.

Usage:
    python cisco_get_schema.py <host> <username> <password> [output_directory]
"""

import sys
import os
import argparse
import re
from typing import Optional, Tuple
from ncclient import manager
from ncclient.xml_ import to_ele
from xml.etree import ElementTree as ET


def _extract_module_and_revision(capability_uri: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract module name and revision from a capability URI.

    Example capability:
      urn:ietf:params:xml:ns:yang:ietf-yang-types?module=ietf-yang-types&revision=2013-07-15
    """
    if "?" not in capability_uri:
        return None, None
    query = capability_uri.split("?", 1)[1]
    module_match = re.search(r"module=([^&]*)", query)
    rev_match = re.search(r"revision=([^&]*)", query)
    module = module_match.group(1) if module_match else None
    revision = rev_match.group(1) if rev_match else None
    return module, revision


def _retrieve_schema_via_rpc(netconf_manager, module_name: str, revision: Optional[str]) -> Optional[str]:
    """Retrieve a YANG schema using the standard get-schema RPC.

    Uses direct RPC to ensure we can parse the <data> payload reliably across vendors.
    """
    # Build RPC body (add <version> only when we have a revision)
    if revision:
        rpc = f"""
<get-schema xmlns="urn:ietf:params:xml:ns:yang:ietf-netconf-monitoring">
  <identifier>{module_name}</identifier>
  <version>{revision}</version>
</get-schema>
"""
    else:
        rpc = f"""
<get-schema xmlns="urn:ietf:params:xml:ns:yang:ietf-netconf-monitoring">
  <identifier>{module_name}</identifier>
</get-schema>
"""
    try:
        reply = netconf_manager.dispatch(to_ele(rpc))
        xml = reply.xml if hasattr(reply, "xml") else str(reply)
        root = ET.fromstring(xml)
        # Find any element whose local-name is 'data'
        schema_text = None
        for elem in root.iter():
            if elem.tag.endswith("data"):
                # The YANG text is usually as text content of <data>
                # Join itertext to preserve line breaks when possible
                schema_text = "".join(elem.itertext())
                break
        if schema_text is None:
            # Fallback: try to get entire reply as a string (last resort)
            return None
        return schema_text
    except Exception as e:
        print(f"Error retrieving schema for {module_name}@{revision or 'latest'}: {e}", file=sys.stderr)
        return None


def _save_schema(output_dir: str, module_name: str, revision: Optional[str], schema_data: str) -> None:
    """Save schema data to a file, using module@revision.yin naming when available."""
    suffix = f"@{revision}" if revision else ""
    filename = os.path.join(output_dir, f"{module_name}{suffix}.yang")
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(schema_data)
        print(f"Schema saved to {filename}")
    except OSError as e:
        print(f"Error saving schema to {filename}: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Retrieve YANG schemas from a Cisco NETCONF device.")
    parser.add_argument("host", help="Device hostname or IP address")
    parser.add_argument("username", help="NETCONF username")
    parser.add_argument("password", help="NETCONF password")
    parser.add_argument("output_dir", nargs="?", default="cisco-schema", help="Output directory (default: cisco-schema)")
    parser.add_argument("--port", type=int, default=830, help="NETCONF port (default: 830)")
    args = parser.parse_args()

    # Create output directory if it doesn't exist
    try:
        os.makedirs(args.output_dir, exist_ok=True)
    except OSError as e:
        print(f"Error creating output directory {args.output_dir}: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        with manager.connect(
            host=args.host,
            port=args.port,
            username=args.username,
            password=args.password,
            hostkey_verify=False,
            device_params={"name": "iosxr"},  # works for XR; also fine for XE/NX-OS for base1.0 ops
            timeout=60,
            allow_agent=False,
            look_for_keys=False,
        ) as m:
            # Iterate over server capabilities and try to fetch schemas for those exposing ?module=
            seen = set()
            for cap in m.server_capabilities:
                module, revision = _extract_module_and_revision(cap)
                if not module:
                    continue
                key = (module, revision)
                if key in seen:
                    continue
                seen.add(key)
                print(f"Retrieving schema for module: {module} revision: {revision or 'latest'}")
                schema = _retrieve_schema_via_rpc(m, module, revision)
                if schema:
                    _save_schema(args.output_dir, module, revision, schema)

    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
