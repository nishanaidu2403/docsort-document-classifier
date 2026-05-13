import os
from datetime import datetime

# This function creates all folders our project needs
def create_folders():

    # List of ALL folders our pipeline needs
    folders = [
        "uploads",                              
        "documents/hr/resumes",                
        "documents/finance/invoices",           
        "documents/finance/paystubs",           
        "documents/legal/contracts",            
        "documents/unknown",                    
        "documents/duplicates",                 
        "documents/miscellaneous/unreadable",   
        "documents/miscellaneous/unsupported",  
        "logs",                                 
        "ml_model",                             
        "training_data/resumes",                
        "training_data/invoices",               
        "training_data/paystubs",               
        "training_data/contracts"               
    ]

    # Go through each folder and create it
    for folder in folders:
        os.makedirs(folder, exist_ok=True)
        print(f"✅ Created: {folder}")

    print("\n🎉 All folders are ready!")


# This function checks the file before processing
def check_file(file_path):

    # Step 1: Check if file even exists
    if not os.path.exists(file_path):
        return {
            "status": "rejected",
            "reason": "File does not exist"
        }

    # Step 2: Get file size in bytes
    file_size = os.path.getsize(file_path)

    # Step 3: Check if file is completely empty
    if file_size == 0:
        return {
            "status": "rejected",
            "reason": "File is completely empty (0 bytes)"
        }

    # Step 4: Check if file is very large (over 50MB)
    fifty_mb = 50 * 1024 * 1024
    if file_size > fifty_mb:
        return {
            "status": "warning",
            "reason": "File is large (over 50MB) - processing may take longer"
        }

    # Step 5: File is fine - continue processing
    return {
        "status": "ok",
        "reason": "File is valid"
    }


# This function generates a processing report
def generate_report(file_name, file_size, file_type,
                    is_duplicate, is_readable,
                    doc_type, destination,
                    time_taken, status):

    size_in_kb = round(file_size / 1024, 2)

    report = f"""
--------------------------------------------------
PROCESSING REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
--------------------------------------------------
file name     : {file_name}
file size     : {size_in_kb} KB
file type     : {file_type}
duplicate     : {is_duplicate}
readable      : {is_readable}
document type : {doc_type}
destination   : {destination}
time taken    : {time_taken} seconds
status        : {status}
--------------------------------------------------
"""

    print(report)

    return report


# Run folder creation when this file is run directly
if __name__ == "__main__":
    create_folders()