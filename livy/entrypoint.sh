#! /bin/bash

set -e

# inject env variables here maybe????????
# sed -i -e "s~\${k8s_api_host}~$SPARK_MASTER_URL~"  /opt/tmp/livy.conf
# sed -i 's~livy.spark.master=.*~livy.spark.master=spark://spark-master:7077~' /opt/tmp/livy.conf
sed -i "s~livy.spark.master=.*~livy.spark.master=$SPARK_MASTER_URL~" /opt/tmp/livy.conf
sed -i "s~livy.file.local-dir-whitelist=.*~livy.file.local-dir-whitelist=/dependency-jars,/opt/spark/cambridgesemantics_jars,/opt/.livy-sessions/~" /opt/tmp/livy.conf

# standanlone spark "spark;//spark-master:7077" doesnt support recovery
sed -i 's~livy.server.recovery.mode=.*~livy.server.recovery.mode=off~' /opt/tmp/livy.conf
# sed -i -e "s~\${spark_kubernetes_namespace}~$POD_NAMESPACE~"  /opt/tmp/spark-defaults.conf
# 
# cat /mount/spark-defaults.conf /opt/tmp/spark-defaults.conf | awk -F= '!($1 in settings) {settings[$1] = $2; print}' >> /opt/spark/conf/spark-defaults.conf
# cat /mount/livy.conf /opt/tmp/livy.conf | awk -F= '!($1 in settings) {settings[$1] = $2; print}' >> /opt/livy/conf/livy.conf
# 

cp /opt/tmp/livy.conf /opt/livy/conf/livy.conf
exec "$@"