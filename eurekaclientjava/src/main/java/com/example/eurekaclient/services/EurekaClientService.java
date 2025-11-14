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

    public boolean registerInstance(ServiceInstance instance) {
        String serviceName = instance.getServiceName().toUpperCase();
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
        String serviceName = instance.getServiceName().toUpperCase();
        String instanceId = instance.getServiceName() + ":" + serviceName + ":" + instance.getHttpPort();
        String heartbeatUrl = eurekaServerUrl + serviceName + "/" + instanceId;

        restTemplate.put(heartbeatUrl, null);
    }

    public void deregisterInstance(ServiceInstance instance) {
        String serviceName = instance.getServiceName().toUpperCase();
        String instanceId = instance.getServiceName() + ":" + serviceName + ":" + instance.getHttpPort();
        String deregisterUrl = eurekaServerUrl + serviceName + "/" + instanceId;

        restTemplate.delete(deregisterUrl);
    }

    private String buildXmlPayload(ServiceInstance instance) {
        return """
            <instance>
            <instanceId>%s:%s:%d</instanceId>
            <hostName>%s</hostName>
            <app>%s</app>
            <ipAddr>%s</ipAddr>
            <vipAddress>%s</vipAddress>
            <secureVipAddress>%s</secureVipAddress>
            <status>%s</status>
            <port enabled="false">%d</port>
            <securePort enabled="true">%d</securePort>
            <homePageUrl>http://%s:%d/</homePageUrl>
            <statusPageUrl>http://%s:%d/actuator/info</statusPageUrl>
            <healthCheckUrl>http://%s:%d/actuator/health</healthCheckUrl>
            <dataCenterInfo class="com.netflix.appinfo.InstanceInfo$DefaultDataCenterInfo">
                <name>%s</name>
            </dataCenterInfo>
            </instance>
            """.formatted(
                instance.getHostName(), instance.getServiceName(), instance.getHttpPort(),
                instance.getHostName(), instance.getServiceName(),
                instance.getIpAddr(),
                instance.getServiceName().toLowerCase(), instance.getServiceName().toLowerCase(),
                instance.getStatus(),
                instance.getHttpPort(), instance.getSecurePort(),
                instance.getHostName(), instance.getHttpPort(),
                instance.getHostName(), instance.getHttpPort(),
                instance.getHostName(), instance.getHttpPort(),
                instance.getDataCenterInfoName()
            );
    }
}
