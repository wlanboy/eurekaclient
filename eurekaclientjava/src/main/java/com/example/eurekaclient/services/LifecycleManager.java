package com.example.eurekaclient.services;

import org.springframework.stereotype.Component;

import java.util.List;
import java.util.stream.Collectors;
import java.util.Map;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;

@Component
public class LifecycleManager {

    private final EurekaClientService eurekaClientService;
    private final ScheduledExecutorService scheduler = Executors.newScheduledThreadPool(5);
    private final Map<Long, ServiceInstance> instanceMap = new ConcurrentHashMap<>();

    // Map für laufende Tasks und Stop-Events
    private final Map<Long, ScheduledFuture<?>> runningTasks = new ConcurrentHashMap<>();
    private final Map<Long, AtomicBoolean> stopEvents = new ConcurrentHashMap<>();

    public LifecycleManager(EurekaClientService eurekaClientService) {
        this.eurekaClientService = eurekaClientService;
    }

    public void startLifecycle(ServiceInstance instance) {
        retryRegister(instance, 0);
    }

    private void retryRegister(ServiceInstance instance, int attempt) {
        boolean registered = eurekaClientService.registerInstance(instance);

        if (registered) {
            System.out.println("[Lifecycle] Registrierung erfolgreich für " + instance.getServiceName());

            AtomicBoolean stopEvent = new AtomicBoolean(false);
            stopEvents.put(instance.getId(), stopEvent);

            ScheduledFuture<?> future = scheduler.scheduleAtFixedRate(() -> {
                if (stopEvent.get()) {
                    System.out.println("[Lifecycle] Stop-Signal empfangen für " + instance.getServiceName());
                    return;
                }
                eurekaClientService.sendHeartbeat(instance);
            }, 0, 20, TimeUnit.SECONDS);

            runningTasks.put(instance.getId(), future);
            instanceMap.put(instance.getId(), instance);

        } else {
            int nextAttempt = attempt + 1;
            long delay = Math.min(60, (long) Math.pow(2, attempt));
            System.out.printf(
                    "[Lifecycle] Registrierung fehlgeschlagen für %s – neuer Versuch in %d Sekunden (Versuch %d)%n",
                    instance.getServiceName(), delay, nextAttempt);

            scheduler.schedule(() -> retryRegister(instance, nextAttempt), delay, TimeUnit.SECONDS);
        }
    }

    public void stopLifecycle(ServiceInstance instance) {
        AtomicBoolean stopEvent = stopEvents.get(instance.getId());
        if (stopEvent != null) {
            stopEvent.set(true);
        }
        ScheduledFuture<?> future = runningTasks.get(instance.getId());
        if (future != null) {
            future.cancel(true);
        }
        eurekaClientService.deregisterInstance(instance);
        System.out.println("[Lifecycle] Instanz gestoppt und deregistriert: " + instance.getServiceName());
    }

    public void stopAll(List<ServiceInstance> instances) {
        for (ServiceInstance instance : instances) {
            stopLifecycle(instance);
        }
        scheduler.shutdown();
    }

    public List<ServiceInstance> getRunningInstances() {
        return runningTasks.keySet().stream()
                .map(id -> {
                    return instanceMap.get(id);
                })
                .collect(Collectors.toList());
    }
}
