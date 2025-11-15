FROM gcr.io/distroless/cc:nonroot
WORKDIR /app
COPY target/eurekaclient .
EXPOSE 8080
USER nonroot
ENTRYPOINT ["/app/eurekaclient"]
