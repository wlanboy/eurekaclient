package com.example.eurekaclient;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

import com.example.eurekaclient.services.LifecycleManager;
import com.example.eurekaclient.services.ServiceInstance;
import com.example.eurekaclient.services.ServiceInstanceRepository;

import jakarta.annotation.PreDestroy;

import java.util.List;

@SpringBootApplication
public class Application {

    private final ServiceInstanceRepository repository;
    private final LifecycleManager lifecycleManager;

    public Application(ServiceInstanceRepository repository, LifecycleManager lifecycleManager) {
        this.repository = repository;
        this.lifecycleManager = lifecycleManager;
    }

    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }

    @PreDestroy
    public void onShutdown() {
        System.out.println(">>> Anwendung wird heruntergefahren – stoppe alle Eureka Clients...");
        List<ServiceInstance> allInstances = repository.findAll();
        lifecycleManager.stopAll(allInstances);
        System.out.println(">>> Alle Clients gestoppt und deregistriert.");
    }
}
