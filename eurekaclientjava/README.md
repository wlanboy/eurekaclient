# Java build

```bash
sdk install java 21-tem
sdk install maven 3.9.9 
mvn package
```

# Docker build
```bash
docker build -t eurekaclient:latest .

docker run --rm -p 8080:8080 \
  --network host \
  -v $(pwd)/services.json:/app/services.json \
  -v $(pwd)/application.properties:/app/application.properties \
  --name eurekaclient \
  eurekaclient:latest
```

# Helm install
```bash
helm install eurekaclient ./eurekaclient-chart
```

# Java Native build
```bash
sdk install java 21.0.2-graalce
sudo apt-get install musl musl-dev musl-tools

export GRAALVM_HOME=~/.sdkman/candidates/java/21.0.2-graalce/

mvn -Pnative -DskipTests -Dspring.aot.enabled=true -Dspring.native.buildArgs="--static --libc=musl" native:compile