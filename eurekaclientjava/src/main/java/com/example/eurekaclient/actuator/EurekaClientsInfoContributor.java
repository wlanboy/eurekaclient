package com.example.eurekaclient.actuator;

import org.springframework.boot.actuate.info.Info;
import org.springframework.boot.actuate.info.InfoContributor;
import org.springframework.stereotype.Component;

import com.example.eurekaclient.services.LifecycleManager;

@Component
public class EurekaClientsInfoContributor implements InfoContributor {

    private final LifecycleManager lifecycleManager;

    public EurekaClientsInfoContributor(LifecycleManager lifecycleManager) {
        this.lifecycleManager = lifecycleManager;
    }

    @Override
    public void contribute(Info.Builder builder) {
        int running = lifecycleManager.getRunningInstances().size();
        builder.withDetail("eurekaClients.runningCount", running);

        lifecycleManager.getRunningInstances().forEach(inst ->
            builder.withDetail("eurekaClients." + inst.getServiceName(),
                    "Status=" + inst.getStatus() )
        );
    }
}

