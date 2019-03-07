#!/bin/bash
docker run --rm -it \
--mount type=bind,src=/dir/with/physlog,dst=/wkdir \
vuphyslog \
python /app/physlog.py \
--pacs_ip nnn.nnn.nnn.nnn \
--pacs_port xxxxx \
--pacs_aetitle AETITLE \
--unique_root a.b.c.d.e.f.g \
--jpg_file /app/vuphyslog.jpg \
--stations_file /wkdir/scanner_stations.json \
--physlog_file /wkdir/SCANPHYSLOGxxxxxxxxxxxxxx.log \
--physlog_scanner SCNR
