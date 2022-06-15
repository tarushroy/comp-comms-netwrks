#!/bin/bash

for num in {1..10}
do
python3 rdp.py localhost 8080 in.txt out.txt
echo ""
diff in.txt out.txt
done
