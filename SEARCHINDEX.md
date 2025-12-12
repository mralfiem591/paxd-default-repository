# PaxD Search Index Documentation

## Overview

The `searchindex.csv` file is an optimization feature that dramatically speeds up package searching in PaxD. Instead of fetching individual package metadata files for every package (which can take 20+ seconds for even small repositories), PaxD can now fetch a single CSV file containing all searchable package information.

## Performance Benefits

- **Before**: ~20 seconds for a 7-package repository (1 HTTP request per package)
- **After**: <1 second (single HTTP request for entire index)
- **Scalability**: Performance improvement increases with repository size

## CSV Format

The `searchindex.csv` file must be placed at the root of your PaxD repository and contains the following columns:

| Column | Description | Example |
|--------|-------------|---------|
| `package_id` | The unique package identifier | `com.mralfiem591.paxd` |
| `package_name` | The display name of the package | `PaxD` |
| `description` | Package description | `The main command line tool for using PaxD.` |
| `author` | Package author | `mralfiem591` |
| `version` | Current package version | `1.6.7` |
| `alias` | Primary command alias | `paxd` |
| `aliases` | All aliases (pipe-separated) | `paxd\|paxdinstaller\|paxdmanager` |
| `is-metapackage` | (Optional) `true` if metapackage, else `false` or empty | `true` |

### Example CSV

```csv
package_id,package_name,description,author,version,alias,aliases,is-metapackage
com.mralfiem591.paxd,PaxD,The main command line tool for using PaxD.,mralfiem591,1.6.7,paxd,paxd|paxdinstaller|paxdmanager,false
com.mralfiem591.paxd-sdk,PaxD SDK,The main SDK for PaxD.,mralfiem591,1.2.4,,paxd-sdk|paxdsdk,false
```

## Generating the Search Index

### Automatic Generation

Use the provided `generate_searchindex.py` script to automatically generate the index from your repository:

```bash
python generate_searchindex.py
```

This script will:
1. Scan all packages in the `packages/` directory
2. Extract metadata from `paxd`, `paxd.yaml`, or `package.yaml` files
3. Load aliases from the `resolution` file
4. Generate `searchindex.csv` at the repository root

### Manual Generation

If you prefer to maintain the index manually, ensure your CSV file:
- Is UTF-8 encoded
- Uses comma separators
- Includes the header row
- Uses pipe (`|`) characters to separate multiple aliases
- Escapes any commas in descriptions with quotes

## Fallback Behavior

PaxD automatically handles repositories without a search index:

1. **Index Available**: Fast search using `searchindex.csv` (1 HTTP request)
2. **Index Missing**: Legacy search by fetching individual package files (slower)

When falling back to legacy search, users will see:
```
Note: Using legacy search (slower). Repository maintainer should add searchindex.csv for better performance.
```

## Repository Maintainer Checklist

To add search index support to your repository:

1. ✅ Generate the index:
   ```bash
   python generate_searchindex.py
   ```

2. ✅ Commit the `searchindex.csv` file to your repository root

3. ✅ Update the index whenever you:
   - Add new packages
   - Update package metadata
   - Change package versions
   - Modify aliases

4. ✅ (Optional) Add index generation to your CI/CD pipeline

## Automated Updates

Consider adding a GitHub Action or pre-commit hook to automatically regenerate the search index:

### GitHub Action Example

```yaml
name: Update Search Index

on:
  push:
    paths:
      - 'packages/**'
      - 'resolution'

jobs:
  update-index:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.x'
      - name: Install dependencies
        run: pip install pyyaml
      - name: Generate search index
        run: python generate_searchindex.py
      - name: Commit changes
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add searchindex.csv
          git commit -m "Update search index" || exit 0
          git push
```

## Troubleshooting

### Search is still slow
- Verify `searchindex.csv` exists at repository root
- Check that the CSV file is properly formatted
- Ensure your repository URL resolves correctly

### Index generation fails
- Verify all packages have valid manifest files (`paxd`, `paxd.yaml`, or `package.yaml`)
- Check that the `resolution` file is valid JSONC
- Ensure you have `pyyaml` installed: `pip install pyyaml`

### Packages missing from search results
- Regenerate the index with `python generate_searchindex.py`
- Verify the package exists in the `packages/` directory
- Check that the package has a valid manifest file

## Technical Details

### Search Process

1. **With Index**:
   ```
   User searches → Fetch searchindex.csv (1 request) → Parse CSV → Filter results
   ```

2. **Without Index (Legacy)**:
   ```
   User searches → Fetch resolution file → For each package:
     - Fetch package manifest (N requests)
     - Parse metadata
     - Check matches
   ```

### Compatibility

- **Required PaxD Version**: 1.6.7+
- **Backward Compatible**: Yes (automatic fallback to legacy search)
- **CSV Encoding**: UTF-8
- **Line Endings**: Unix (LF) or Windows (CRLF) both supported

## Future Enhancements

Potential improvements for future versions:

- Gzip compression for large repositories
- Caching with ETags to reduce bandwidth
- JSON format support as alternative to CSV
- Incremental index updates
- Full-text search scoring/ranking
