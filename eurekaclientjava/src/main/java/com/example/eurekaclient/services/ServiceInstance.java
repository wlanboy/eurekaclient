package com.example.eurekaclient.services;

public class ServiceInstance {
    private Long id;

    private String serviceName;
    private String hostName;
    private int httpPort;
    private int securePort;
    private String ipAddr;
    private String dataCenterInfoName;
    private String status;
    private boolean sslPreferred;

    // Getters and Setters
    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getServiceName() {
        return serviceName;
    }

    public void setServiceName(String serviceName) {
        this.serviceName = serviceName;
    }

    public String getHostName() {
        return hostName;
    }

    public void setHostName(String hostName) {
        this.hostName = hostName;
    }

    public int getHttpPort() {
        return httpPort;
    }

    public void setHttpPort(int httpPort) {
        this.httpPort = httpPort;
    }

    public int getSecurePort() {
        return securePort;
    }

    public void setSecurePort(int securePort) {
        this.securePort = securePort;
    }

    public String getDataCenterInfoName() {
        return dataCenterInfoName;
    }

    public void setDataCenterInfoName(String dataCenterInfoName) {
        this.dataCenterInfoName = dataCenterInfoName;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }
    
    public String getIpAddr() {
        return ipAddr;
    }

    public void setIpAddr(String ipAddr) {
        this.ipAddr = ipAddr;
    }

    public boolean isSslPreferred() {
        return sslPreferred;
    }

    public void setSslPreferred(boolean sslPreferred) {
        this.sslPreferred = sslPreferred;
    }
}
