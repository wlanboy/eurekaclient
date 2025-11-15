package com.example.eurekaclient;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

import com.example.eurekaclient.services.LifecycleManager;
import com.example.eurekaclient.services.ServiceInstance;
import com.example.eurekaclient.services.ServiceInstanceStore;

import jakarta.annotation.PreDestroy;

import java.util.List;

@SpringBootApplication
public class Application {

    private final ServiceInstanceStore store;
    private final LifecycleManager lifecycleManager;

    public Application(ServiceInstanceStore store, LifecycleManager lifecycleManager) {
        this.store = store;
        this.lifecycleManager = lifecycleManager;
    }

    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }

    @PreDestroy
    public void onShutdown() {
        System.out.println(">>> Anwendung wird heruntergefahren – stoppe alle Eureka Clients...");
        List<ServiceInstance> allInstances = store.getInstances();
        lifecycleManager.stopAll(allInstances);
        System.out.println(">>> Alle Clients gestoppt und deregistriert.");
    }
}
