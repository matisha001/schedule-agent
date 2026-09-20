# Elasticsearch 单节点镜像 + IK 中文分词插件
# 若安装插件网络失败，可去掉本文件改用官方镜像：image: docker.elastic.co/elasticsearch/elasticsearch:8.x
FROM docker.elastic.co/elasticsearch/elasticsearch:8.17.0

RUN bin/elasticsearch-plugin install --batch https://get.infini.cloud/elasticsearch/analysis-ik/8.17.0 \
    || bin/elasticsearch-plugin install --batch https://github.com/infinilabs/analysis-ik/releases/download/v8.17.0/elasticsearch-analysis-ik-8.17.0.zip
