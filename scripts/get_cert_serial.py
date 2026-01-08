"""
Helper script to get WeChat Pay certificate serial number
"""
import os
import sys
import subprocess

def get_cert_serial_from_file(cert_path):
    """Get certificate serial number from certificate file"""
    try:
        # Try using openssl command
        result = subprocess.run(
            ['openssl', 'x509', '-in', cert_path, '-noout', '-serial'],
            capture_output=True,
            text=True,
            check=True
        )
        serial = result.stdout.strip()
        # Remove 'serial=' prefix if present
        if serial.startswith('serial='):
            serial = serial[7:]
        return serial
    except subprocess.CalledProcessError:
        return None
    except FileNotFoundError:
        print("Error: openssl command not found. Please install OpenSSL.")
        return None

def get_cert_serial_from_python(cert_path):
    """Get certificate serial number using Python cryptography library"""
    try:
        from cryptography import x509
        from cryptography.hazmat.backends import default_backend
        
        with open(cert_path, 'rb') as f:
            cert = x509.load_pem_x509_certificate(f.read(), default_backend())
            serial = str(cert.serial_number)
            return serial
    except ImportError:
        print("Error: cryptography library not installed.")
        print("Install it with: pip install cryptography")
        return None
    except Exception as e:
        print(f"Error reading certificate: {e}")
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python get_cert_serial.py <cert_file_path>")
        print("Example: python get_cert_serial.py ./certs/apiclient_cert.pem")
        sys.exit(1)
    
    cert_path = sys.argv[1]
    
    if not os.path.exists(cert_path):
        print(f"Error: Certificate file not found: {cert_path}")
        sys.exit(1)
    
    print(f"Reading certificate from: {cert_path}")
    
    # Try openssl first
    serial = get_cert_serial_from_file(cert_path)
    
    # If openssl fails, try Python
    if not serial:
        print("Trying Python cryptography library...")
        serial = get_cert_serial_from_python(cert_path)
    
    if serial:
        print(f"\nCertificate Serial Number: {serial}")
        print(f"\nAdd this to your .env file:")
        print(f"WECHAT_CERT_SERIAL_NO={serial}")
    else:
        print("\nFailed to get certificate serial number.")
        print("Please check:")
        print("1. Certificate file path is correct")
        print("2. OpenSSL is installed (or cryptography library)")
        sys.exit(1)

if __name__ == '__main__':
    main()

