import sys
import os
import subprocess

def custom_sort_key(s):
    return (0, s) if 'Schema' in s else (1, s)

if __name__ == "__main__":
    prnumber = sys.argv[1]
    current_directory = os.path.dirname(os.path.abspath(__file__))
    GetModifiedFiles = f'git diff --name-only origin/main "{current_directory}/../../../Sample Data/ASIM/"'
    try:
        modified_files = subprocess.run(GetModifiedFiles, shell=True, text=True, capture_output=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"::error::An error occurred while executing the command: {e}")
        sys.stdout.flush()  # Explicitly flush stdout
    
# Sort the array using the custom sort key
    sorted_array = sorted(modified_files.stdout.splitlines(), key=custom_sort_key)

# Print the sorted array
    print(sorted_array)
    print(prnumber)
