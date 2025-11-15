package com.example.eurekaclient.actuator;

import org.springframework.boot.actuate.health.Health;
import org.springframework.boot.actuate.health.HealthIndicator;
import org.springframework.stereotype.Component;

import com.example.eurekaclient.services.LifecycleManager;

@Component
public class EurekaClientsHealthIndicator implements HealthIndicator {

    private final LifecycleManager lifecycleManager;

    public EurekaClientsHealthIndicator(LifecycleManager lifecycleManager) {
        this.lifecycleManager = lifecycleManager;
    }

    @Override
    public Health health() {
        var running = lifecycleManager.getRunningInstances();

        if (running.isEmpty()) {
            return Health.down()
                    .withDetail("eurekaClients", "Keine Instanzen laufen")
                    .build();
        }

        boolean allUp = running.stream()
                .allMatch(inst -> "UP".equalsIgnoreCase(inst.getStatus()));

        if (allUp) {
            return Health.up()
                    .withDetail("eurekaClients", running.size() + " Instanzen laufen")
                    .build();
        } else {
            return Health.down()
                    .withDetail("eurekaClients", "Nicht alle Instanzen sind UP")
                    .withDetail("running", running.size())
                    .build();
        }
    }
}

