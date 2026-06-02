import os

def main():
    app_path = "app.py"
    if not os.path.exists(app_path):
        return
        
    with open(app_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Replacements matching the exact \ufffd characters
    replacements = {
        "analista t\ufffdcnica s\ufffdnior": "analista t\ufffdcnico s\ufffdnior",
        "nossa analista t\ufffdcnica": "nosso analista t\ufffdcnico",
        "pela analista t\ufffdcnica": "pelo analista t\ufffdcnico"
    }
    
    for old_str, new_str in replacements.items():
        content = content.replace(old_str, new_str)
            
    with open(app_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    print("Successfully completed gender fix silently!")

if __name__ == "__main__":
    main()
