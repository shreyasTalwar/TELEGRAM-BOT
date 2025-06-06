import os
import sys
import atexit

# Global variable to store the lock file handle
lock_file = None
lock_filename = None

def acquire_lock():
    """
    Try to acquire a lock to ensure only one instance of the bot is running.
    Returns True if lock was acquired, False otherwise.
    Uses Windows-compatible file locking.
    """
    global lock_file, lock_filename
    
    # Create a lock file in the same directory as the script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    lock_filename = os.path.join(script_dir, "bot.lock")
    
    try:
        # Try to open the file in exclusive creation mode
        # This will fail if the file already exists
        lock_file = open(lock_filename, "x")
        
        # Write the process ID to the file
        lock_file.write(str(os.getpid()))
        lock_file.flush()
        
        # Register cleanup function
        atexit.register(release_lock)
        
        print("Lock acquired successfully. This is the only running instance.")
        return True
        
    except FileExistsError:
        # Lock file exists, check if it's stale
        try:
            with open(lock_filename, "r") as f:
                pid = int(f.read().strip())
            
            # Check if the process with this PID is still running
            try:
                # This works on Windows
                import ctypes
                kernel32 = ctypes.windll.kernel32
                PROCESS_QUERY_INFORMATION = 0x0400
                process = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION, 0, pid)
                
                if process:
                    kernel32.CloseHandle(process)
                    print(f"ERROR: Another instance (PID {pid}) is already running.")
                    return False
                else:
                    # Process doesn't exist, the lock is stale
                    os.remove(lock_filename)
                    # Try again
                    return acquire_lock()
            except:
                # If we can't check, assume the process is running
                print(f"ERROR: Another instance (PID {pid}) may be running.")
                return False
                
        except (ValueError, IOError):
            # Couldn't read PID or file is corrupted
            os.remove(lock_filename)
            # Try again
            return acquire_lock()
            
        except Exception as e:
            print(f"ERROR: Failed to check lock: {e}")
            return False

def release_lock():
    """
    Release the lock file.
    """
    global lock_file, lock_filename
    
    if lock_file:
        lock_file.close()
        
    if lock_filename and os.path.exists(lock_filename):
        try:
            os.remove(lock_filename)
            print("Lock released.")
        except Exception as e:
            print(f"Warning: Failed to remove lock file: {e}")
