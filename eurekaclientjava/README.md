# Java build

```bash
sdk install java 21-tem
sdk install maven 3.9.9 
mvn package
```

# Java Native build
```bash
sdk install java 21.0.2-graalce
export GRAALVM_HOME=~/.sdkman/candidates/java/21.0.2-graalce/

mvn -Pnative -DskipTests -Dspring.aot.enabled=true -Dspring.native.buildArgs="--static --libc=musl" native:compile

docker build -t eurekaclient:native .
docker run -p 8080:8080 eurekaclient:native

```
