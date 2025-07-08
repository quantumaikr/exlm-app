#!/bin/bash

# Fix Python 3.9 compatibility issues

echo "Fixing Python 3.9 compatibility issues..."

# Find all Python files and replace | with Optional/Union
find backend/app -name "*.py" -type f -exec grep -l " | None" {} \; | while read file; do
    echo "Fixing $file"
    # Add Optional import if not present
    if ! grep -q "from typing import.*Optional" "$file"; then
        if grep -q "from typing import" "$file"; then
            sed -i '' 's/from typing import/from typing import Optional, /' "$file"
            sed -i '' 's/Optional, Optional,/Optional,/' "$file"
        else
            sed -i '' '1s/^/from typing import Optional\n/' "$file"
        fi
    fi
    # Replace | None with Optional[]
    sed -i '' -E 's/: ([A-Za-z_][A-Za-z0-9_\[\]]*) \| None/: Optional[\1]/g' "$file"
    sed -i '' -E 's/-> ([A-Za-z_][A-Za-z0-9_\[\]]*) \| None/-> Optional[\1]/g' "$file"
done

# Fix List[str] | None patterns
find backend/app -name "*.py" -type f -exec grep -l "List\[.*\] | None" {} \; | while read file; do
    echo "Fixing List patterns in $file"
    sed -i '' -E 's/: (List\[[^]]+\]) \| None/: Optional[\1]/g' "$file"
    sed -i '' -E 's/-> (List\[[^]]+\]) \| None/-> Optional[\1]/g' "$file"
done

# Fix Dict patterns
find backend/app -name "*.py" -type f -exec grep -l "Dict\[.*\] | None" {} \; | while read file; do
    echo "Fixing Dict patterns in $file"
    sed -i '' -E 's/: (Dict\[[^]]+\]) \| None/: Optional[\1]/g' "$file"
    sed -i '' -E 's/-> (Dict\[[^]]+\]) \| None/-> Optional[\1]/g' "$file"
done

echo "Compatibility fixes applied!"