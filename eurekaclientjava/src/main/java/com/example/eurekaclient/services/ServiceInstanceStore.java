package com.example.eurekaclient.services;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

import jakarta.annotation.PostConstruct;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.io.File;
import java.io.FileInputStream;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicLong;

@Component
public class ServiceInstanceStore {

    private final List<ServiceInstance> instances = new ArrayList<>();
    private final AtomicLong idCounter = new AtomicLong(1);

    @Value("${store.json.path}")
    private String jsonFilePath;

    @PostConstruct
    public void init() {
        try {
            ObjectMapper mapper = new ObjectMapper();
            File file = new File(jsonFilePath);
            try (InputStream is = new FileInputStream(file)) {
                List<ServiceInstance> loaded = mapper.readValue(is, new TypeReference<List<ServiceInstance>>() {});
                for (ServiceInstance instance : loaded) {
                    if (instance.getId() == null) {
                        instance.setId(idCounter.getAndIncrement());
                    }
                    instances.add(instance);
                }
                System.out.println("[Store] " + instances.size() + " Instanzen aus " + jsonFilePath + " geladen.");
            }
        } catch (Exception e) {
            throw new RuntimeException("Konnte services.json nicht laden von " + jsonFilePath, e);
        }
    }

    public List<ServiceInstance> getInstances() {
        return instances;
    }

    public ServiceInstance findByServiceNameAndHostNameAndHttpPort(String serviceName, String hostName, int httpPort) {
        return instances.stream()
                .filter(i -> i.getServiceName().equalsIgnoreCase(serviceName)
                        && i.getHostName().equalsIgnoreCase(hostName)
                        && i.getHttpPort() == httpPort)
                .findFirst()
                .orElse(null);
    }

    public void save(ServiceInstance existing) {
        if (existing.getId() == null) {
            existing.setId(idCounter.getAndIncrement());
        }
        ServiceInstance found = findByServiceNameAndHostNameAndHttpPort(
                existing.getServiceName(),
                existing.getHostName(),
                existing.getHttpPort()
        );
        if (found != null) {
            instances.remove(found);
        }
        instances.add(existing);
    }
}
