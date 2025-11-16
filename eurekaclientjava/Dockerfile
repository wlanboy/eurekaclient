FROM registry.access.redhat.com/ubi8/openjdk-21-runtime

WORKDIR /app
COPY target/eurekaclient-0.0.1-SNAPSHOT.jar /app/eurekaclient.jar

EXPOSE 8080

ENTRYPOINT ["java", "-Djava.security.egd=file:/dev/./urandom", "-jar", "/app/eurekaclient.jar"]
