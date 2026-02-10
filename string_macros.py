name: String Macros (numbered subfolders)

on:
  workflow_dispatch:
    inputs:
      versions:
        description: 'How many versions per folder'
        required: true
        default: '6'
      target_minutes:
        description: 'Target duration per merged file'
        required: true
        default: '35'
      enable_chat:
        description: 'Enable chat inserts'
        required: false
        default: true
        type: boolean

permissions:
  contents: write

jobs:
  string:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'
          
      - name: Get current BUNDLE_SEQ
        id: seq
        run: |
          if [ -f .github/string_bundle_counter.txt ]; then
            VAL=$(cat .github/string_bundle_counter.txt)
          else
            VAL=1
          fi
          echo "BUNDLE_SEQ=$VAL" >> "$GITHUB_ENV"
        
      - name: Execute string macro script
        run: |
          # Check if script exists
          if [ ! -f "string_macros.py" ]; then
            echo "❌ ERROR: string_macros.py not found in repository root!"
            echo ""
            echo "Please ensure string_macros.py is committed to the repository."
            echo "Expected location: /string_macros.py (in root directory)"
            echo ""
            ls -la
            exit 1
          fi
          
          mkdir -p output
          
          # Build command
          CMD="python3 string_macros.py string_input output"
          CMD="$CMD --versions ${{ github.event.inputs.versions }}"
          CMD="$CMD --target-minutes ${{ github.event.inputs.target_minutes }}"
          CMD="$CMD --bundle-id ${{ env.BUNDLE_SEQ }}"
          
          # Add --no-chat if disabled
          if [ "${{ inputs.enable_chat }}" = "false" ]; then
            CMD="$CMD --no-chat"
            echo "🔕 Chat inserts DISABLED"
          else
            echo "✅ Chat inserts ENABLED"
          fi
          
          # Execute
          echo "Running: $CMD"
          $CMD
            
      - name: Commit and Push Counter Update
        run: |
          NEW_VAL=$((BUNDLE_SEQ + 1))
          mkdir -p .github
          echo "$NEW_VAL" > .github/string_bundle_counter.txt
          git config --global user.name 'github-actions[bot]'
          git config --global user.email 'github-actions[bot]@users.noreply.github.com'
          git add .github/string_bundle_counter.txt
          git commit -m "Increment string bundle counter to $NEW_VAL" || echo "No changes"
          git push || echo "Push failed"
            
      - name: Create ZIP artifact
        run: |
          BUNDLE_NAME="stringed_bundle_${{ env.BUNDLE_SEQ }}"
          ZIP_FILE="stringed_macros_${{ env.BUNDLE_SEQ }}.zip"
          
          echo "Checking output directory:"
          ls -R output/ || echo "Output directory is empty or doesn't exist"
          
          if [ ! -d "output/$BUNDLE_NAME" ]; then
            echo "❌ Error: Directory output/$BUNDLE_NAME was not found!"
            echo ""
            echo "This usually means:"
            echo "  1. No folders with numbered subfolders were found in string_input/"
            echo "  2. The script didn't create any output files"
            echo ""
            echo "Please check:"
            echo "  - string_input/ exists and has folders"
            echo "  - Folders contain numbered subfolders (1/, 2/, 3/)"
            echo "  - Numbered subfolders contain .json files"
            echo ""
            echo "Example structure:"
            echo "  string_input/"
            echo "  └── 57- My Task/"
            echo "      ├── 1/"
            echo "      │   ├── file1.json"
            echo "      │   └── file2.json"
            echo "      ├── 2/"
            echo "      │   └── action.json"
            echo "      └── 3/"
            echo "          └── return.json"
            exit 1
          fi
          
          # Check if bundle has any files
          if [ -z "$(ls -A output/$BUNDLE_NAME)" ]; then
            echo "❌ Error: Bundle directory exists but is empty!"
            echo "No files were created. Check script output above."
            exit 1
          fi
          
          cd output && zip -r "../$ZIP_FILE" "$BUNDLE_NAME"
          echo "FINAL_ZIP=$ZIP_FILE" >> "$GITHUB_ENV"
          
      - name: Upload stringed ZIP artifact
        uses: actions/upload-artifact@v4
        with:
          name: stringed_macros_bundle_${{ env.BUNDLE_SEQ }}
          path: ${{ env.FINAL_ZIP }}
