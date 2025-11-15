package com.example.eurekaclient.services;

import java.util.List;

import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

@Service
public class EurekaClientService {

    private final RestTemplate restTemplate = new RestTemplate();
    private final String eurekaServerUrl = System.getenv()
            .getOrDefault("EUREKA_SERVER_URL", "http://localhost:8761/eureka/apps/");

    public String generateInstanceId(ServiceInstance instance) {
        int port = instance.isSslPreferred() ? instance.getSecurePort() : instance.getHttpPort();
        return String.format("%s:%s:%d", instance.getHostName(), instance.getServiceName(), port);
    }

    public String generateServiceName(ServiceInstance instance) {
        if (instance.getServiceName() == null) {
            return "UNKNOWN";
        }
        return instance.getServiceName().trim().toUpperCase();
    }

    public boolean registerInstance(ServiceInstance instance) {
        String serviceName = generateServiceName(instance);
        String appUrl = eurekaServerUrl + serviceName;

        String xmlPayload = buildXmlPayload(instance);

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_XML);
        headers.setAccept(List.of(MediaType.APPLICATION_XML));

        HttpEntity<String> request = new HttpEntity<>(xmlPayload, headers);

        try {
            ResponseEntity<String> response = restTemplate.postForEntity(appUrl, request, String.class);
            return response.getStatusCode() == HttpStatus.NO_CONTENT;
        } catch (Exception e) {
            return false;
        }
    }

    public void sendHeartbeat(ServiceInstance instance) {
        String serviceName = generateServiceName(instance);
        String instanceId = generateInstanceId(instance);
        String heartbeatUrl = eurekaServerUrl + serviceName + "/" + instanceId;

        restTemplate.put(heartbeatUrl, null);
    }

    public void deregisterInstance(ServiceInstance instance) {
        String serviceName = generateServiceName(instance);
        String instanceId = generateInstanceId(instance);
        String deregisterUrl = eurekaServerUrl + serviceName + "/" + instanceId;

        restTemplate.delete(deregisterUrl);
    }

    private String buildXmlPayload(ServiceInstance instance) {
        // Entscheide, ob SSL bevorzugt wird
        boolean ssl = instance.isSslPreferred();

        String portEnabled = ssl ? "false" : "true";
        String secureEnabled = ssl ? "true" : "false";

        // Wähle Protokoll und Port
        String protocol = ssl ? "https" : "http";
        int port = ssl ? instance.getSecurePort() : instance.getHttpPort();

        return """
                <instance>
                  <instanceId>%s:%s:%d</instanceId>
                  <hostName>%s</hostName>
                  <app>%s</app>
                  <ipAddr>%s</ipAddr>
                  <vipAddress>%s</vipAddress>
                  <secureVipAddress>%s</secureVipAddress>
                  <status>%s</status>
                  <port enabled="%s">%d</port>
                  <securePort enabled="%s">%d</securePort>
                  <homePageUrl>%s://%s:%d/</homePageUrl>
                  <statusPageUrl>%s://%s:%d/actuator/info</statusPageUrl>
                  <healthCheckUrl>%s://%s:%d/actuator/health</healthCheckUrl>
                  <dataCenterInfo class="com.netflix.appinfo.InstanceInfo$DefaultDataCenterInfo">
                    <name>%s</name>
                  </dataCenterInfo>
                </instance>
                """.formatted(
                instance.getHostName(), instance.getServiceName(), port,
                instance.getHostName(), instance.getServiceName(),
                instance.getIpAddr(),
                instance.getServiceName().toLowerCase(), instance.getServiceName().toLowerCase(),
                instance.getStatus(),
                portEnabled, instance.getHttpPort(),
                secureEnabled, instance.getSecurePort(),
                protocol, instance.getHostName(), port,
                protocol, instance.getHostName(), port,
                protocol, instance.getHostName(), port,
                instance.getDataCenterInfoName());
    }

}
