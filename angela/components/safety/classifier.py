# angela/safety/classifier.py
"""
Command and operation risk classification system for Angela CLI.

This module is responsible for determining the risk level of commands 
and operations to ensure appropriate confirmation and safety measures.
It provides comprehensive coverage of Linux commands, including those
from common packages and specialized tools.
"""
import re
import shlex
from typing import List, Dict, Tuple, Set, Optional

from angela.constants import RISK_LEVELS
from angela.utils.logging import get_logger

logger = get_logger(__name__)

# Define risk patterns for shell commands
RISK_PATTERNS = {
    # Critical risk - destructive operations with system-wide impact
    RISK_LEVELS["CRITICAL"]: [
        # System-level removal operations
        (r"^rm\s+.*((-r|-rf|-R|--recursive)\s+(/|/boot|/etc|/bin|/sbin|/lib|/usr|/var)\b|--)", "System directory removal"),
        (r"^rmdir\s+.*((/boot|/etc|/bin|/sbin|/lib|/usr|/var)\b)", "System directory removal"),
        
        # Disk formatting/partitioning
        (r"^(mkfs|fdisk|dd|shred|wipefs)\b", "Disk formatting/partitioning/wiping"), 
        (r"^mkfs\.[a-z0-9]+\s+(/dev/sd|/dev/nvme|/dev/xvd|/dev/vd|/dev/mapper)", "Filesystem creation on disk device"),
        (r"^(sgdisk|gdisk|parted|gparted)\s+.*(--zap|--clear|-c|-z|-o|mkpart|rm)", "Partition table modification"),
        
        # Direct device access
        (r"^dd\s+.*if=/dev/(zero|random|urandom).*of=/dev/(sd|hd|nvme|md|xvd|vd|mapper)", "Direct device writing"),
        
        # System shutdown/power
        (r"^(shutdown|poweroff|reboot|halt|init\s+(0|6))\b", "System power control"),
        
        # Network interface disabling system-wide
        (r"^ip\s+link\s+set\s+dev\s+(eth0|ens|wlan|bond|wlp|enp)\S*\s+down", "Network interface disabling"),
        
        # Dangerous firewall changes
        (r"^(iptables|ufw)\s+.*(?:\s|^)(-F|--flush|-P\s+INPUT\s+DROP|-P\s+FORWARD\s+DROP)", "Firewall flushing/blocking"),
        
        # System configuration with risk of lockout
        (r"^passwd\s+root", "Root password change"),
        (r"^usermod\s+.*(-G\s+.*|--groups\s+.*)sudo.*root", "Changing root/sudo access"),
        
        # System bootloader modification
        (r"^(grub-install|efibootmgr\s+.*-c)\b", "Bootloader modification"),
    ],
    
    # High risk - significant system changes
    RISK_LEVELS["HIGH"]: [
        # File removal operations (not targeting system directories)
        (r"^rm\s+.*(-r|-rf|-R|--recursive)\b", "Recursive file deletion"),
        (r"^rm\s+.*(-f|--force)\b", "Forced file deletion"),
        
        # Moving files with potential data loss
        (r"^mv\s+.*(-f|--force)\b", "Forced file movement"),
        
        # Package management
        (r"^(apt|apt-get|yum|dnf|pacman|zypper|brew)\s+(install|remove|purge|autoremove)", "Package installation/removal"),
        (r"^pip\s+(install|uninstall)", "Python package installation/removal"),
        (r"^npm\s+(install|uninstall)\s+(-g|--global)", "Global NPM package installation/removal"),
        
        # User and group management
        (r"^(useradd|userdel|groupadd|groupdel|usermod|groupmod)\b", "User/group management"),
        
        # Privilege operations
        (r"^su\s+(?!-c)", "User switching"),
        (r"^sudo\s+.*\bnash\b", "Command execution as root"),
        
        # Network configuration
        (r"^(ifconfig|ip)\s+.*(?:netmask|broadcast|add|del|up|down)\b", "Network interface configuration"),
        (r"^route\s+(add|del)", "Routing table modification"),
        
        # System service management
        (r"^systemctl\s+(enable|disable|start|stop|restart|mask)\b", "System service management"),
        (r"^service\s+.*\s+(start|stop|restart)\b", "Service control"),
        
        # Permissions/ownership - system directories
        (r"^chmod\s+.*(/boot|/etc|/bin|/sbin|/lib|/usr|/var)", "Changing permissions in system directories"),
        (r"^chown\s+.*(/boot|/etc|/bin|/sbin|/lib|/usr|/var)", "Changing ownership in system directories"),
        
        # Permissions/ownership - recursive or wide-ranging
        (r"^chmod\s+.*(777|a\+[rwx]{3})\b", "Setting world-writable permissions"),
        (r"^chmod\s+.*(-R|--recursive)\b", "Recursive permission changes"),
        (r"^chown\s+.*(-R|--recursive)\b", "Recursive ownership changes"),
        
        # Mount operations
        (r"^mount\s+(/dev/|[^/ ]+:/)", "Mounting filesystems"),
        (r"^umount\s+(/|/home|/mnt|/media)", "Unmounting filesystems"),
        
        # Shell history manipulation
        (r"^history\s+(-c|--clear)", "Clearing shell history"),
        
        # Partition changes
        (r"^(fdisk|gdisk|parted|partprobe)\b", "Partition management"),
        
        # Firewall configuration
        (r"^(ufw|firewall-cmd|iptables)\b", "Firewall configuration"),
        
        # Database administration
        (r"^(mysql|psql|mongo)\s+.*(-e\s+\"DROP|\"DELETE FROM)", "Database data deletion"),
        
        # Network scanning/penetration testing
        (r"^(nmap|nikto|sqlmap|aircrack-ng|metasploit)\b", "Network scanning/penetration testing"),
    ],
    
    # Medium risk - file modifications and information gathering that could be sensitive
    RISK_LEVELS["MEDIUM"]: [
        # File modification
        (r"(>|>>)\s*[\w\./-]+", "Writing to files"),
        (r"^(nano|vim|vi|emacs|sed|truncate)\s+[\w\./-]+", "File editing"),
        
        # Symbolic links
        (r"^ln\s+(-s|--symbolic)\s+", "Creating symbolic links"),
        
        # File transfer
        (r"^(scp|rsync|sftp)\s+", "File transfer"),
        
        # Network tools with potential impact
        (r"^ssh\s+-R", "SSH reverse tunneling"),
        (r"^nc\s+(-l|--listen)", "NetCat listening"),
        (r"^curl\s+.*--output", "Downloading files"),
        (r"^wget\s+", "Downloading files"),
        
        # Disk usage scanning
        (r"^du\s+.*(-a|-h|--all)", "Disk usage scanning"),
        
        # Process management
        (r"^kill\s+", "Process termination"),
        (r"^(pkill|killall)\s+", "Process termination by name"),
        
        # Compression/archiving
        (r"^(zip|tar|gzip|bzip2|xz)\s+.*(-d|--decompress|-x|--extract)", "Archive extraction"),
        (r"^(zip|tar|gzip|bzip2|xz)\s+.*(-c|--create)", "Archive creation"),
        
        # System information gathering
        (r"^(strace|ltrace|ptrace)\b", "Process tracing"),
        (r"^tcpdump\b", "Network packet capture"),
        
        # Docker operations
        (r"^docker\s+(run|exec|build|rm|stop)", "Docker container operations"),
        
        # Database operations
        (r"^(mysql|psql|mongo|sqlite3)\b", "Database operations"),
        
        # Web servers
        (r"^(apache2|nginx|httpd)\b", "Web server control"),
        
        # User sensitive data display
        (r"^(who|w|last|lastlog)\b", "User login information"),
        
        # Kali Linux tools - information gathering
        (r"^(dirb|dirbuster|enum4linux|gobuster|wpscan|dnsrecon)\b", "Information gathering tools"),
        
        # Configuration changes
        (r"^(update-alternatives|alternatives)\s+--set", "System alternative configuration"),
        
        # Script execution
        (r"\bsh\s+[^\|;]+\.sh\b", "Shell script execution"),
        (r"\bbash\s+[^\|;]+\.sh\b", "Bash script execution"),
        
        # Unusual file operations
        (r"^shred\s+", "Secure file deletion"),
        
        # Package operations other than install/remove
        (r"^(apt|apt-get|yum|dnf|pacman)\s+(update|upgrade|dist-upgrade)", "Package system update"),
        
        # System logs
        (r"^(journalctl|dmesg)\s+.*-f", "Viewing system logs"),
        
        # Chroot operations
        (r"^chroot\s+", "Changing root directory"),
        
        # Cron job editing
        (r"^(crontab)\s+(-e|--edit)", "Cron job editing"),
        
        # Configuration file editing
        (r"^(visudo)\b", "Sudoers file editing"),
        
        # NetworkManager
        (r"^nmcli\s+c(on)?(nection)?\s+(add|mod|delete)", "NetworkManager configuration"),
        
        # User configuration
        (r"^usermod\s+", "User account modification"),
        
        # Git operations that affect history
        (r"^git\s+(reset|rebase|push\s+.*--force)", "Git history modification"),
        
        # SSH key generation
        (r"^ssh-keygen\b", "SSH key generation"),
        
        # Package building
        (r"^(dpkg-buildpackage|rpmbuild)\b", "Package building"),
        
        # LDAP operations
        (r"^ldap(search|add|modify|delete)\b", "LDAP operations"),
        
        # Ruby gems
        (r"^gem\s+(install|uninstall)", "Ruby gem management"),
        
        # Go package management
        (r"^go\s+get\b", "Go package installation"),
        
        # Ifconfig/ip
        (r"^ifconfig\b", "Network interface configuration display/modification"),
    ],
    
    # Low risk - creating files/dirs without overwriting, and most informational tools
    RISK_LEVELS["LOW"]: [
        # Making directories
        (r"^mkdir\s+", "Creating directory"),
        
        # Touching files
        (r"^touch\s+", "Creating/updating file timestamp"),
        
        # Copying files
        (r"^cp\s+(?!.*(-f|--force))", "Copying files (non-forced)"),
        
        # Utility commands
        (r"^(tee|split|join|paste|sort|uniq)\b", "Text processing"),
        (r"^(gzip|bzip2|xz|zip|tar)\s+(?!.*(-d|--decompress|-x|--extract))", "File compression"),
        
        # Git operations (non-destructive)
        (r"^git\s+(add|commit|fetch|pull|clone)", "Git repository operations"),
        
        # Process viewing
        (r"^(ps|top|htop|pstree)\b", "Process viewing"),
        
        # Text viewing with paging
        (r"^(more|less|most)\b", "Text viewing with paging"),
        
        # Network status
        (r"^(ping|traceroute|mtr|dig|nslookup|host)\b", "Network diagnostics"),
        
        # Directory navigation
        (r"^(cd|pushd|popd)\b", "Directory navigation"),
        
        # File searching
        (r"^(which|whereis|type)\b", "Command location"),
        
        # System information
        (r"^(uname|hostname|uptime|free|df)\b", "System information"),
        
        # User identification
        (r"^(id|groups|whoami)\b", "User identification"),
        
        # Terminal utilities
        (r"^(screen|tmux|tput|reset|clear)\b", "Terminal utilities"),
        
        # Basic utilities
        (r"^(date|cal|bc|expr)\b", "Basic utilities"),
        
        # SSH (without options that can impact system)
        (r"^ssh\s+(?!.*-R)[\w\.@:-]+", "SSH connection"),
        
        # Docker inspection
        (r"^docker\s+(ps|images|inspect|logs)", "Docker inspection"),
        
        # Package queries
        (r"^(apt|apt-get|yum|dnf|pacman)\s+(search|list|info|show)", "Package queries"),
        
        # Archive listing
        (r"^(zip|tar|gzip|bzip2|xz)\s+.*(-t|--list)", "Archive listing"),
        
        # Python scripts
        (r"^python[23]?\s+[\w\./-]+", "Python script execution"),
        
        # Node.js scripts
        (r"^node\s+[\w\./-]+", "Node.js script execution"),
        
        # Shell utilities
        (r"^(basename|dirname|realpath|readlink)\b", "Path manipulation"),
        
        # Disk tools
        (r"^(fdisk|gdisk|parted)\s+.*-l", "Partition listing"),
        
        # Systemd queries
        (r"^systemctl\s+(status|list-units|is-enabled|is-active)", "Systemd service queries"),
        
        # Network status
        (r"^(netstat|ss|lsof)\b", "Network connection status"),
        
        # Container inspection
        (r"^(docker|podman|lxc)\s+(ps|images|info|version)", "Container inspection"),
        
        # Text processing
        (r"^(awk|sed|cut|tr|head|tail)\s+.*", "Text processing"),
    ],
    
    # Safe - read-only operations
    RISK_LEVELS["SAFE"]: [
        # File listing operations
        (r"^ls\s+", "Listing files"),
        (r"^dir\s+", "Listing files"),
        (r"^tree\s+", "Listing files in tree format"),
        (r"^ll\s+", "Listing files with details"),
        (r"^file\s+", "Determining file type"),
        (r"^stat\s+", "Displaying file status"),
        
        # Reading files
        (r"^(cat|tac|rev|od|xxd|hexdump)\s+", "Reading file content"),
        (r"^(head|tail)\s+", "Reading file content"),
        (r"^(grep|egrep|fgrep|rg|ag)\s+", "Searching file content"),
        
        # Finding files
        (r"^find\s+", "Finding files"),
        (r"^locate\s+", "Finding files using database"),
        
        # Viewing disk usage
        (r"^du\s+(?!.*-a)", "Checking disk usage"),
        (r"^df\s+", "Checking filesystem space"),
        
        # Getting working directory
        (r"^pwd\s*", "Printing working directory"),
        
        # Man pages and help
        (r"^man\s+", "Displaying manual pages"),
        (r"^info\s+", "Displaying info documents"),
        (r"^help\s+", "Displaying help information"),
        (r"^whatis\s+", "Displaying command description"),
        (r"^apropos\s+", "Searching man pages"),
        
        # System information
        (r"^(lscpu|lspci|lsusb|lsblk|lsmod|lshw|inxi)\b", "Listing hardware/modules"),
        (r"^(vmstat|iostat|mpstat|sar)\b", "Displaying system statistics"),
        
        # Environment variables
        (r"^(env|printenv|set)\b", "Displaying environment variables"),
        
        # Version information
        (r"^.*(-v|--version)\b", "Displaying version information"),
        (r"^version\b", "Displaying version information"),
        
        # Calendar, date and time
        (r"^(date|cal|ncal)\b", "Displaying date or calendar"),
        
        # Network status (read-only)
        (r"^ip\s+(addr|link|route)\s+(show|list|ls)\b", "Displaying network information"),
        (r"^(ifconfig|iwconfig|arp)\s+(?!.*\b(up|down|add|del))", "Displaying network information"),
        
        # Process information (read-only)
        (r"^(pgrep|pidof)\b", "Finding process IDs"),
        
        # History recall
        (r"^history\s+(?!-c)", "Displaying command history"),
        
        # Echo and printing
        (r"^(echo|printf)\b", "Printing text"),
        
        # Hash calculation
        (r"^(md5sum|sha1sum|sha256sum|sha512sum)\b", "Calculating file hash"),
        
        # Text viewing
        (r"^(wc|nl|expand|fold|fmt)\b", "Text viewing/formatting"),
        
        # Package information
        (r"^(dpkg|rpm)\s+(-l|--list|-q|--query)", "Listing installed packages"),
        
        # Systemd information
        (r"^systemctl\s+list", "Listing systemd units"),
        
        # Git information
        (r"^git\s+(status|log|diff|show|branch|tag)", "Git repository information"),
        
        # SSH checks
        (r"^ssh\s+-T", "Testing SSH connection"),
        
        # Docker information
        (r"^docker\s+(info|version)", "Docker information"),
        
        # Certificates
        (r"^openssl\s+x509\s+-text", "Displaying certificate information"),
        
        # Network diagnostic (read-only)
        (r"^(ping|traceroute|tracepath|mtr)\s+(-c\s+\d+|--count=\d+)?", "Network connectivity testing"),
        
        # DNS querying
        (r"^(dig|host|nslookup)\b", "DNS querying"),
        
        # Filesystem type
        (r"^(df|lsblk|blkid|findmnt)\b", "Filesystem information"),
        
        # Basic shell built-ins
        (r"^(alias|type|hash|true|false|test|[)\b", "Shell built-ins"),
        
        # Time-based commands
        (r"^time\s+", "Timing command execution"),
        
        # System call tracing (read-only)
        (r"^strace\s+-c", "Counting system calls"),
        
        # Weather information
        (r"^(curl|wget)\s+(wttr\.in|v2\.wttr\.in)", "Weather information"),
    ],
}

# Special case patterns that override normal classification
OVERRIDE_PATTERNS = {
    # Force certain operations to be safe
    "SAFE": [
        # Basic grep-like operations
        r"^grep\s+(-r|--recursive)?\s+[\w\s]+\s+[\w\s\./-]+$",  # Basic grep with fixed strings
        r"^find\s+[\w\s\./-]+\s+-name\s+[\w\s\*\./-]+$",  # Basic find by name
        r"^locate\s+[\w\s\*\./-]+$",  # Basic locate
        
        # Basic ls-like operations
        r"^ls\s+(-l|-a|--all|--long|--color|--human-readable|-h|-la|-lh|-lah)\s*[\w\s\./-]*$",  # Common ls variants
        
        # View file content - safe operations
        r"^cat\s+[\w\s\./-]+$",  # Basic cat
        r"^less\s+[\w\s\./-]+$",  # Basic less
        r"^head\s+(-n\s+\d+|--lines=\d+)?\s+[\w\s\./-]+$",  # Head with optional line count
        r"^tail\s+(-n\s+\d+|--lines=\d+)?\s+[\w\s\./-]+$",  # Tail with optional line count
        
        # System information operations
        r"^(ps|pstree)\s+(-ef|-aux|-e|-a|--forest)$",  # Common ps variants
        r"^(top|htop|atop|btop)\s+(-d\s+\d+|--delay=\d+)?$",  # Process viewers
        
        # Network information 
        r"^(ifconfig|ip\s+addr(\s+show)?|iwconfig|netstat|ss)$",  # Network status commands
        r"^ping\s+(-c\s+\d+)?\s+[\w\.-]+$",  # Basic ping
        
        # File system information
        r"^df\s+(-h|--human-readable)?$",  # Disk free space
        r"^du\s+(-sh|--summary\s+--human-readable)?\s+[\w\s\./-]*$",  # Disk usage
        
        # Basic git operations
        r"^git\s+(status|log|branch|fetch|pull|diff|show)(\s+[\w\.-]+)?$",  # Common git commands
    ],
    
    # Operations that should always be considered critical regardless of base command
    "CRITICAL": [
        # Dangerous rm patterns
        r"[\s;|`]+rm\s+(-r|-f|--recursive|--force)\s+[~/]",  # rm commands affecting home or root
        r"[\s;|`]+rm\s+(-r|-f|--recursive|--force)\s+\.\.",  # rm with parent directory references
        
        # Dangerous disk operations
        r"[\s;|`]+dd\s+(if=/dev/zero|of=/dev/sd|bs=[0-9]+[mM])",  # dd to write to disks
        r"[\s;|`]+shred\s+(/dev/sd|/dev/hd|/dev/nvme)",  # shred on disk devices
        
        # Dangerous redirects to system files
        r">\s*(/etc/passwd|/etc/shadow|/etc/sudoers|/etc/ssh/sshd_config)",  # Writing to critical system files
        
        # Hidden dangerous operations
        r";\s*rm\s+(-r|-f|--recursive|--force)",  # Hidden deletion commands
        
        # Web download + execute
        r"(curl|wget).*\|\s*(bash|sh|ksh|zsh|fish)",  # Downloading and executing scripts
        
        # Disk fill attacks
        r"(dd|fallocate)\s+.*if=/dev/zero.*of=[^/]",  # Creating large files
        
        # Dangerous loops
        r"for\s+.*\s+in\s+.*;.*rm\s+",  # Shell loops with file deletion
        
        # Fork bombs
        r":\(\)\s*{\s*:\s*\|\s*:\s*&\s*}\s*;:",  # Classic fork bomb
        
        # Password/key exposure
        r"(AWS_SECRET_ACCESS_KEY|DB_PASSWORD|MYSQL_ROOT_PASSWORD)=",  # Exposing sensitive credentials
    ],
    
    # Operations that should be considered high risk
    "HIGH": [
        # System permission changes
        r"chmod\s+[0-7][0-7][0-7]\s+/etc/",  # Changing permissions on system config
        r"chown\s+\S+\s+/etc/",  # Changing ownership on system config
        
        # Network service exposure
        r"(iptables|ufw)\s+.*--dport\s+(22|3389)",  # Opening SSH/RDP ports
        
        # sudo execution within commands
        r"\|\s*sudo\s+",  # Piping to sudo
        r"&&\s*sudo\s+",  # Command chaining with sudo
        
        # Configuration file modifications
        r">\s*/etc/",  # Redirecting output to /etc/ 
    ],
    
    # Operations that should be considered medium risk
    "MEDIUM": [
        # Shell redirections
        r">\s*[^/]",  # Simple output redirection
        r">>\s*[^/]",  # Append redirection
        
        # SSH with potential security implications
        r"ssh\s+.*-L",  # SSH port forwarding
        
        # Curl with potential for unexpected results
        r"curl\s+.*--output\s+\S+",  # Curl downloading files
    ],
}



class CommandRiskClassifier:
    """Classifier for command risk levels."""
    
    def classify(self, command: str) -> Tuple[int, str]:
        """
        Classify the risk level of a shell command.
        
        Args:
            command: The shell command to classify.
            
        Returns:
            A tuple of (risk_level, reason).
        """
        if not command.strip():
            return RISK_LEVELS["SAFE"], "Empty command"

        # Check override patterns first
        for level_name, patterns in OVERRIDE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, command):
                    level = RISK_LEVELS[level_name]
                    return level, f"Matched override pattern for {level_name} risk"

        # Check regular risk patterns
        for level, patterns in sorted(RISK_PATTERNS.items(), key=lambda x: x[0], reverse=True):
            for pattern, reason in patterns:
                if re.search(pattern, command.strip()):
                    return level, reason

        # If no pattern matches, default to MEDIUM for unrecognized commands
        # This is a deliberate choice to be cautious with unknown commands
        return RISK_LEVELS["MEDIUM"], "Unrecognized command type"

    def analyze_impact(self, command: str) -> Dict[str, any]:
        """
        Analyze the potential impact of a command.
        
        Args:
            command: The shell command to analyze.
            
        Returns:
            A dictionary containing impact analysis.
        """
        impact = {
            "affected_files": set(),
            "affected_dirs": set(),
            "operations": [],
            "destructive": False,
            "creates_files": False,
            "modifies_files": False,
        }
        
        try:
            tokens = shlex.split(command)
            if not tokens:
                return impact
                
            base_cmd = tokens[0]
            args = tokens[1:]
            
            # Mark certain commands as destructive by default
            if base_cmd in ['rm', 'shred', 'dd', 'mkfs', 'fdisk', 'gdisk', 'parted']:
                impact["destructive"] = True
                
            # Mark certain commands as file creators by default
            if base_cmd in ['touch', 'mkdir', 'cp', 'mv', 'git clone', 'wget', 'curl']:
                impact["creates_files"] = True
                
            # Mark certain commands as file modifiers by default
            if base_cmd in ['vim', 'nano', 'emacs', 'sed', 'awk', 'patch', 'truncate']:
                impact["modifies_files"] = True
                
            # Look for file/directory arguments
            non_option_args = [arg for arg in args if not arg.startswith('-')]
            
            # Basic operation type detection
            if base_cmd in ['ls', 'cat', 'less', 'more', 'head', 'tail', 'grep']:
                impact["operations"].append("read")
            elif base_cmd in ['rm', 'rmdir', 'shred']:
                impact["operations"].append("delete")
            elif base_cmd == 'mv':
                impact["operations"].append("move")
            elif base_cmd == 'cp':
                impact["operations"].append("copy")
            elif base_cmd in ['touch', 'mkdir', 'mknod']:
                impact["operations"].append("create")
            elif base_cmd in ['chmod', 'chown', 'chgrp', 'setfacl']:
                impact["operations"].append("change_attributes")
            elif base_cmd in ['wget', 'curl']:
                impact["operations"].append("download")
            elif base_cmd in ['git', 'svn', 'hg']:
                impact["operations"].append("version_control")
            elif base_cmd in ['apt', 'apt-get', 'yum', 'dnf', 'pacman', 'zypper']:
                impact["operations"].append("package_management")
            elif base_cmd in ['systemctl', 'service']:
                impact["operations"].append("service_management")
            elif base_cmd in ['docker', 'podman', 'kubectl']:
                impact["operations"].append("container_management")
            elif base_cmd in ['ifconfig', 'ip', 'route', 'iptables', 'ufw']:
                impact["operations"].append("network_configuration")
            elif base_cmd in ['passwd', 'useradd', 'usermod', 'groupadd']:
                impact["operations"].append("user_management")
            else:
                impact["operations"].append("unknown")
                
            # Advanced file operation analysis
            for arg in non_option_args:
                # Skip options and redirection symbols
                if arg in ['>', '>>', '<', '|', '&']:
                    continue
                    
                # Try to determine if this is a file or directory argument
                # Simple heuristic: if it ends with / it's a directory
                if arg.endswith('/'):
                    impact["affected_dirs"].add(arg)
                # If it contains a wildcard, treat as both file and directory pattern
                elif '*' in arg or '?' in arg:
                    impact["affected_files"].add(arg)
                    impact["affected_dirs"].add(arg)
                # Otherwise, guess based on command context
                elif base_cmd in ['mkdir', 'rmdir', 'cd', 'pushd', 'popd']:
                    impact["affected_dirs"].add(arg)
                elif '/' in arg:
                    # If there's a path separator, examine the path structure
                    # Is the last component likely a file or directory?
                    if '.' in arg.split('/')[-1]:
                        impact["affected_files"].add(arg)
                    else:
                        impact["affected_dirs"].add(arg)
                else:
                    # Default assumption based on command
                    if base_cmd in ['cat', 'less', 'more', 'touch', 'rm', 'mv', 'cp']:
                        impact["affected_files"].add(arg)
                    else:
                        # When really uncertain, add to both
                        impact["affected_files"].add(arg)
        
        except Exception as e:
            logger.exception(f"Error analyzing command impact for '{command}': {str(e)}")
        
        # Convert sets to lists for easier serialization
        impact["affected_files"] = list(impact["affected_files"])
        impact["affected_dirs"] = list(impact["affected_dirs"])
        
        return impact
        
# Create a global instance of the classifier
command_risk_classifier = CommandRiskClassifier()
