package com.example.eurekaclient.services;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.boot.ApplicationRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.io.File;
import java.util.List;

@Configuration
public class StartupService {

    @Bean
    public ApplicationRunner importAndStartServices(ServiceInstanceStore store,
                                                    LifecycleManager lifecycleManager) {
        return args -> {
            File file = new File("services.json");
            if (file.exists()) {
                try {
                    ObjectMapper mapper = new ObjectMapper();
                    List<ServiceInstance> instances = mapper.readValue(
                            file,
                            new TypeReference<List<ServiceInstance>>() {}
                    );

                    for (ServiceInstance instance : instances) {
                        ServiceInstance existing = store.findByServiceNameAndHostNameAndHttpPort(
                                instance.getServiceName(),
                                instance.getHostName(),
                                instance.getHttpPort()
                        );

                        if (existing != null) {
                            existing.setSecurePort(instance.getSecurePort());
                            existing.setDataCenterInfoName(instance.getDataCenterInfoName());
                            existing.setStatus(instance.getStatus());
                            existing.setIpAddr(instance.getIpAddr());
                            store.save(existing);
                            System.out.println("Aktualisiert: " + existing.getServiceName());
                        } else {
                            store.save(instance);
                            System.out.println("Neu importiert: " + instance.getServiceName());
                        }
                    }
                } catch (Exception e) {
                    System.err.println("Fehler beim Import von services.json: " + e.getMessage());
                }
            } else {
                System.out.println("Keine services.json gefunden – überspringe Import.");
            }

            // Jetzt alle Instanzen aus der DB holen und Lifecycle starten
            List<ServiceInstance> allInstances = store.getInstances();
            for (ServiceInstance instance : allInstances) {
                lifecycleManager.startLifecycle(instance);
                System.out.println("Lifecycle gestartet für: " + instance.getServiceName());
            }
        };
    }
}
