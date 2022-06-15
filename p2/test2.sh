#!/bin/bash

for num in {1..10}
do
python3 rdp.py localhost 8080 rdp_backup.py rdp_out.txt
echo ""
diff rdp_backup.py rdp_out.txt
done
