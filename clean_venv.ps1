Write-Host "Cleaning virtual environment..."

# 1. List all installed packages
.\.venv\Scripts\pip.exe freeze > uninstall_list.txt

# 2. Uninstall everything
if (Test-Path uninstall_list.txt) {
    .\.venv\Scripts\pip.exe uninstall -r uninstall_list.txt -y
    Remove-Item uninstall_list.txt
}

# 3. Reinstall strictly from requirements.txt
.\.venv\Scripts\pip.exe install -r requirements.txt

Write-Host "Environment clean and ready!"
