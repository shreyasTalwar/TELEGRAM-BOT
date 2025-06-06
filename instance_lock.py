# instance_lock.py - Refactored for Robustness

import os
import sys
import time # Added for small delay in acquire retry

# For Windows process checking
if os.name == 'nt':
    import ctypes
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_VM_READ = 0x0010 # Not strictly needed for existence check, but often included
    STILL_ACTIVE = 259 # From Windows API, status for a running process

class InstanceLock:
    def __init__(self, lock_filename="bot.lock"):
        # Place lock file in the same directory as this script, or a specified path
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.lock_filename = os.path.join(base_dir, lock_filename)
        self.lock_file = None
        print(f"[InstanceLock] Initialized. Lock file path: {self.lock_filename}", flush=True)

    def is_process_running_windows(self, pid: int) -> bool:
        print(f"[is_process_running_windows] Checking if PID {pid} is running", flush=True)
        if pid <= 0: # Invalid PID
            print(f"[is_process_running_windows] Invalid PID {pid} (<=0). Assuming not running.", flush=True)
            return False
        
        try:
            process_handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION, False, pid)
            if process_handle == 0: # Null handle
                error_code = kernel32.GetLastError()
                # ERROR_INVALID_PARAMETER (87) often means process not found or access denied
                # ERROR_ACCESS_DENIED (5)
                print(f"[is_process_running_windows] OpenProcess failed for PID {pid}. Error code: {error_code}. Assuming not running.", flush=True)
                return False

            exit_code = ctypes.c_ulong()
            if kernel32.GetExitCodeProcess(process_handle, ctypes.byref(exit_code)):
                kernel32.CloseHandle(process_handle)
                is_active = exit_code.value == STILL_ACTIVE
                print(f"[is_process_running_windows] PID {pid} GetExitCodeProcess result: {exit_code.value}. Active: {is_active}", flush=True)
                return is_active
            else:
                error_code = kernel32.GetLastError()
                print(f"[is_process_running_windows] GetExitCodeProcess failed for PID {pid}. Error code: {error_code}. Assuming not running.", flush=True)
                kernel32.CloseHandle(process_handle)
                return False
        except Exception as e:
            print(f"[is_process_running_windows] Exception checking PID {pid}: {e}. Assuming not running.", flush=True)
            return False

    def is_process_running_posix(self, pid: int) -> bool:
        print(f"[is_process_running_posix] Checking if PID {pid} is running", flush=True)
        if pid <= 0:
            print(f"[is_process_running_posix] Invalid PID {pid}. Assuming not running.", flush=True)
            return False
        try:
            os.kill(pid, 0)  # Send signal 0, doesn't kill but checks existence/permissions
        except OSError as err:
            # ESRCH means process does not exist
            # EPERM means process exists but we don't have permission (still running)
            if err.errno == errno.ESRCH:
                print(f"[is_process_running_posix] PID {pid} does not exist (ESRCH).", flush=True)
                return False
            elif err.errno == errno.EPERM:
                print(f"[is_process_running_posix] PID {pid} exists but no permission (EPERM). Assuming running.", flush=True)
                return True # Process exists
            else: # Other OSError
                print(f"[is_process_running_posix] OSError checking PID {pid}: {err}. Assuming not running.", flush=True)
                return False
        except Exception as e: # Other exceptions
             print(f"[is_process_running_posix] Exception checking PID {pid}: {e}. Assuming not running.", flush=True)
             return False
        print(f"[is_process_running_posix] PID {pid} seems to be running (os.kill(pid,0) succeeded).", flush=True)
        return True # Process exists

    def is_process_running(self, pid: int) -> bool:
        if os.name == 'nt':
            return self.is_process_running_windows(pid)
        elif os.name == 'posix':
            global errno # Needs import errno at the top for POSIX
            import errno # Import here to keep it local to POSIX path
            return self.is_process_running_posix(pid)
        else:
            print(f"[is_process_running] Unsupported OS: {os.name}. Cannot check process status reliably.", flush=True)
            return False # Or raise an error, or assume running to be safe

    def check_and_remove_stale_lock(self):
        """
        Checks if the existing lock file is stale. If stale, removes it.
        Returns True if a stale lock was found and removed (or file was corrupt/empty and removed),
        False otherwise (lock is active, file not found, or error during check/removal).
        """
        print(f"[check_and_remove_stale_lock] Checking for stale lock file: {self.lock_filename}", flush=True)
        try:
            with open(self.lock_filename, "r") as f:
                locked_pid_str = f.read().strip()
                if not locked_pid_str: # Empty lock file
                    print(f"[check_and_remove_stale_lock] Lock file is empty. Treating as stale.", flush=True)
                    os.remove(self.lock_filename)
                    print(f"[check_and_remove_stale_lock] Removed empty lock file: {self.lock_filename}", flush=True)
                    return True # Stale and removed

                locked_pid = int(locked_pid_str)
            print(f"[check_and_remove_stale_lock] Found PID {locked_pid} in lock file.", flush=True)

            if not self.is_process_running(locked_pid):
                print(f"[check_and_remove_stale_lock] Process {locked_pid} (from lock file) is NOT running. Stale lock detected.", flush=True)
                os.remove(self.lock_filename)
                print(f"[check_and_remove_stale_lock] Stale lock file {self.lock_filename} removed.", flush=True)
                return True # Stale and removed
            else:
                print(f"[check_and_remove_stale_lock] Process {locked_pid} (from lock file) IS running. Lock is active.", flush=True)
                return False # Not stale

        except FileNotFoundError:
            print(f"[check_and_remove_stale_lock] Lock file {self.lock_filename} not found. Nothing to check or remove.", flush=True)
            return False # No lock file, so not stale in the sense of needing removal
        except ValueError: # If lock file content is not an int
            print(f"[check_and_remove_stale_lock] ERROR: Lock file {self.lock_filename} contains non-integer PID. Treating as stale.", flush=True)
            try:
                os.remove(self.lock_filename) # Remove corrupted lock file
                print(f"[check_and_remove_stale_lock] Removed corrupted lock file {self.lock_filename}.", flush=True)
            except Exception as e_remove_corrupt:
                print(f"[check_and_remove_stale_lock] ERROR: Failed to remove corrupted lock file: {e_remove_corrupt}", flush=True)
            return True # Corrupt, attempted removal
        except Exception as e:
            print(f"[check_and_remove_stale_lock] ERROR: General failure in check_and_remove_stale_lock: {e}", flush=True)
            return False # Uncertain state, safer to assume lock is active or problem exists

    def acquire(self):
        current_pid = os.getpid()
        print(f"[acquire] PID {current_pid}: Attempting to acquire lock ({self.lock_filename})", flush=True)
        
        for attempt in range(3): # Max 3 attempts to handle race conditions
            try:
                # Attempt to create the lock file exclusively
                self.lock_file = open(self.lock_filename, "x")
                self.lock_file.write(str(current_pid))
                self.lock_file.flush()
                print(f"[acquire] PID {current_pid}: Lock acquired successfully (Attempt {attempt + 1}).", flush=True)
                # The main script (BOT2_PythonAnywhere.py) should register self.release with atexit.
                return True
            except FileExistsError:
                print(f"[acquire] PID {current_pid}: Lock file exists (Attempt {attempt + 1}). Checking if stale.", flush=True)
                if self.check_and_remove_stale_lock():
                    # Stale lock was found and removed (or file was corrupted and removed)
                    print(f"[acquire] PID {current_pid}: Stale/corrupt lock was removed. Retrying acquisition...", flush=True)
                    if attempt < 2 : # If not the last attempt
                         time.sleep(0.05 * (attempt + 1)) # Brief, slightly increasing pause
                    continue # Go to the next attempt in the loop
                else:
                    # Lock exists and is active, or check_and_remove_stale_lock failed to clear it
                    print(f"[acquire] PID {current_pid}: Lock file exists and is active or could not be cleared. Failed to acquire.", flush=True)
                    return False # Failed to acquire
            except Exception as e:
                print(f"[acquire] PID {current_pid}: ERROR during lock acquisition (Attempt {attempt + 1}): {e}", flush=True)
                # If an unexpected error occurs, stop trying
                return False 
        
        print(f"[acquire] PID {current_pid}: Failed to acquire lock after multiple attempts.", flush=True)
        return False

    def release(self):
        current_pid = os.getpid()
        print(f"[release] PID {current_pid}: Attempting to release lock ({self.lock_filename})", flush=True)
        try:
            if self.lock_file and not self.lock_file.closed:
                print(f"[release] PID {current_pid}: Closing open lock_file handle.", flush=True)
                self.lock_file.close()
            self.lock_file = None # Reset file handle associated with this instance

            # Check PID in file before deleting, only if current process owns it.
            # This is important for atexit cleanup.
            if os.path.exists(self.lock_filename):
                pid_in_file_str = ""
                try:
                    with open(self.lock_filename, "r") as f:
                        pid_in_file_str = f.read().strip()
                    
                    if not pid_in_file_str: # Empty lock file
                        print(f"[release] PID {current_pid}: Lock file {self.lock_filename} is empty. Removing.", flush=True)
                        os.remove(self.lock_filename)
                        print(f"[release] PID {current_pid}: Empty lock file {self.lock_filename} removed.", flush=True)
                        return

                    pid_in_file = int(pid_in_file_str)
                    if pid_in_file == current_pid:
                        print(f"[release] PID {current_pid} matches lock file PID {pid_in_file}. Removing {self.lock_filename}", flush=True)
                        os.remove(self.lock_filename)
                        print(f"[release] PID {current_pid}: Lock file {self.lock_filename} removed.", flush=True)
                    else:
                        print(f"[release] PID {current_pid}: WARNING: Lock file PID {pid_in_file} doesn't match current PID {current_pid}. Not removing (this instance didn't own it).", flush=True)
                
                except ValueError: # Corrupted lock file (non-integer content)
                    print(f"[release] PID {current_pid}: Lock file {self.lock_filename} contains non-integer ('{pid_in_file_str}'). Removing corrupted lock.", flush=True)
                    os.remove(self.lock_filename)
                    print(f"[release] PID {current_pid}: Corrupted lock file {self.lock_filename} removed.", flush=True)
                except FileNotFoundError: # Race condition: file removed between os.path.exists and open
                     print(f"[release] PID {current_pid}: Lock file {self.lock_filename} disappeared before PID check. Nothing to release.", flush=True)
                except Exception as e_read_remove: # Other errors during read/conditional remove
                    print(f"[release] PID {current_pid}: Error during conditional removal of {self.lock_filename}: {e_read_remove}. File may still exist.", flush=True)
            else:
                print(f"[release] PID {current_pid}: Lock file {self.lock_filename} does not exist. Nothing to release.", flush=True)
        except Exception as e:
            print(f"[release] PID {current_pid}: ERROR: General failure in release lock: {e}", flush=True)
