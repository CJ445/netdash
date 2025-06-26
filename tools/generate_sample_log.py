#!/usr/bin/env python3
"""
Generate a sample auth.log file for testing NetDash without root access
"""

import os
import random
from datetime import datetime, timedelta
import argparse

def generate_sample_log(output_path):
    """Generate a sample auth.log file"""
    
    # Sample usernames and IPs
    usernames = ["alice", "bob", "carol", "dave", "admin", "root", "user1", "testuser"]
    ips = ["192.168.1.100", "192.168.1.101", "10.0.0.25", "172.16.0.5", 
           "8.8.8.8", "1.1.1.1", "192.168.0.55"]
    
    # Event templates
    events = [
        # Failed login events
        "sshd[{pid}]: Failed password for {user} from {ip} port {port} ssh2",
        "sshd[{pid}]: Failed password for invalid user {user} from {ip} port {port} ssh2",
        "sshd[{pid}]: error: maximum authentication attempts exceeded for {user} from {ip} port {port} ssh2",
        "sshd[{pid}]: Disconnected from authenticating user {user} {ip} port {port}",
        
        # Successful login events
        "sshd[{pid}]: Accepted password for {user} from {ip} port {port} ssh2",
        "sshd[{pid}]: Accepted publickey for {user} from {ip} port {port} ssh2",
        
        # Sudo events
        "sudo: {user} : TTY=pts/0 ; PWD=/home/{user} ; USER=root ; COMMAND=/usr/bin/apt update",
        "sudo: {user} : TTY=pts/1 ; PWD=/home/{user} ; USER=root ; COMMAND=/bin/cat /etc/shadow",
        "sudo: {user} : TTY=pts/2 ; PWD=/var/log ; USER=root ; COMMAND=/bin/grep -i error auth.log",
        
        # Session events
        "systemd-logind[{pid}]: New session {sess_id} of user {user}.",
        "systemd-logind[{pid}]: Removed session {sess_id}.",
        "systemd[{pid}]: pam_unix(cron:session): session opened for user {user} by (uid=0)",
        "systemd[{pid}]: pam_unix(cron:session): session closed for user {user}"
    ]
    
    # Generate events
    log_entries = []
    event_time = datetime.now() - timedelta(hours=6)  # Start 6 hours ago
    
    for i in range(200):  # Generate 200 log entries
        # Increment time by a random amount
        event_time += timedelta(seconds=random.randint(30, 300))
        
        # Select a random event template
        event_template = random.choice(events)
        
        # Fill in the template
        event = event_template.format(
            pid=random.randint(1000, 9999),
            user=random.choice(usernames),
            ip=random.choice(ips),
            port=random.randint(10000, 65000),
            sess_id=random.randint(1000, 9999)
        )
        
        # Format the timestamp (syslog format: Jun 26 09:30:01)
        timestamp = event_time.strftime("%b %d %H:%M:%S")
        hostname = "localhost"
        
        # Create the full log entry
        log_entries.append(f"{timestamp} {hostname} {event}")
    
    # Generate concentrated failed login attempts for one user
    attack_time = datetime.now() - timedelta(minutes=30)
    attack_user = random.choice(usernames)
    attack_ip = random.choice(ips)
    
    for i in range(10):  # 10 failed attempts in quick succession
        attack_time += timedelta(seconds=random.randint(5, 20))
        timestamp = attack_time.strftime("%b %d %H:%M:%S")
        
        # Failed login attempt
        event = f"sshd[{random.randint(1000, 9999)}]: Failed password for {attack_user} from {attack_ip} port {random.randint(10000, 65000)} ssh2"
        log_entries.append(f"{timestamp} {hostname} {event}")
    
    # Sort entries by timestamp
    log_entries.sort()
    
    # Write to file
    with open(output_path, "w") as f:
        for entry in log_entries:
            f.write(entry + "\n")
    
    print(f"Generated sample log file at {output_path}")
    print(f"Contains {len(log_entries)} events, including a brute force attempt against user {attack_user}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a sample auth.log for testing")
    parser.add_argument("--output", default=os.path.expanduser("~/sample_auth.log"),
                        help="Output path for the sample log file")
    
    args = parser.parse_args()
    generate_sample_log(args.output)
