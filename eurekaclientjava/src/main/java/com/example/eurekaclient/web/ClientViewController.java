package com.example.eurekaclient.web;

import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;

import com.example.eurekaclient.services.ServiceInstanceRepository;

    @Controller
    public class ClientViewController {
        
        private final ServiceInstanceRepository repository;

        public ClientViewController(ServiceInstanceRepository repository) {
            this.repository = repository;
        }

        @GetMapping("/")
        public String defaultView(Model model) {
            model.addAttribute("clients", repository.findAll());
            return "clients"; 
        }

        @GetMapping("/clients")
        public String listClients(Model model) {
            model.addAttribute("clients", repository.findAll());
            return "clients"; 
        }
}
