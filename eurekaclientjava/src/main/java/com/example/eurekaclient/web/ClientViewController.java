package com.example.eurekaclient.web;

import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;

import com.example.eurekaclient.services.LifecycleManager;
import com.example.eurekaclient.services.ServiceInstance;
import com.example.eurekaclient.services.ServiceInstanceStore;

import java.util.List;

@Controller
public class ClientViewController {

    private final ServiceInstanceStore store;
    private final LifecycleManager lifecycleManager;

    public ClientViewController(ServiceInstanceStore store,
                                LifecycleManager lifecycleManager) {
        this.store = store;
        this.lifecycleManager = lifecycleManager;
    }

    // Default View "/"
    @GetMapping("/")
    public String defaultView(Model model) {
        return listClients(model);
    }

    // Clients View "/clients"
    @GetMapping("/clients")
    public String listClients(Model model) {
        List<ServiceInstance> dbClients = store.getInstances();
        List<ServiceInstance> runningClients = lifecycleManager.getRunningInstances();

        model.addAttribute("dbClients", dbClients);
        model.addAttribute("runningClients", runningClients);

        return "clients"; 
    }
}
