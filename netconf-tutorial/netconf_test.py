from ncclient import manager
import xml.dom.minidom  # For pretty-printing XML (optional, for debugging)
import argparse  # For command-line arguments
import yaml      # For config file

def connect_to_device(hostname, username, password, port=830, device_type='default'):
    """Connects to a NETCONF device."""
    try:
        conn = manager.connect(
            host=hostname,
            port=port,
            username=username,
            password=password,
            hostkey_verify=False,  
            device_params={'name': device_type},
            allow_agent=False,
            look_for_keys=False
        )
        print(f"Successfully connected to {hostname}")
        return conn
    except Exception as e:
        print(f"Error connecting to {hostname}: {e}")
        raise

def load_payload(payload_path):
    """Loads a NETCONF payload from an XML file."""
    try:
        with open(payload_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: Payload file not found: {payload_path}")
        raise
    except Exception as e:
        print(f"Error reading payload file: {e}")
        raise

def send_config(session, payload):
    """Sends a NETCONF configuration to the device."""
    try:
        reply = session.edit_config(target='candidate', config=payload)
        # Pretty-print the XML reply (for debugging/demo purposes)
        print("Attempting to send configuration...")
        print(xml.dom.minidom.parseString(str(reply)).toprettyxml())
        return reply

    except Exception as e:
        print(f"Error sending configuration: {e}")
        raise

def commit_config(session):
    """Commits the configuration changes."""
    try:
        reply = session.commit()
        print("Attempting to commit configuration...")
        print(xml.dom.minidom.parseString(str(reply)).toprettyxml())
        return reply
    except Exception as e:
        print(f"Error committing configuration: {e}")
        raise

def load_config(config_file):
    """Loads configuration from a YAML file."""
    try:
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file not found: {config_file}")
        raise
    except Exception as e:
        print(f"Error reading configuration file: {e}")
        raise

def main():
    """Main function to orchestrate the NETCONF operations."""
    parser = argparse.ArgumentParser(description="NETCONF Configuration Script")
    parser.add_argument("-c", "--config", required=True, help="Path to the YAML configuration file")
    parser.add_argument("-p", "--payload", required=True, help="Path to the XML payload file")
    args = parser.parse_args()

    try:
        config = load_config(args.config)
        hostname = config['device']['hostname']
        username = config['device']['username']
        password = config['device']['password']
        port = config['device'].get('port', 830) # Default to 830 if not specified
        device_type = config['device']['type'] 

        session = connect_to_device(hostname, username, password, port, device_type)
        payload = load_payload(args.payload)
        send_config(session, payload)
        commit_config(session)

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if 'session' in locals() and session.connected:
            session.close_session()
            print("NETCONF session closed.")

if __name__ == "__main__":
    main()