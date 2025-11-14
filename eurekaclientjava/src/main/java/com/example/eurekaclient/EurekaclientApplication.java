package com.example.eurekaclient;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.stereotype.Component;

import com.example.eurekaclient.services.EurekaClientService;
import com.example.eurekaclient.services.ServiceInstanceRepository;

import jakarta.annotation.PreDestroy;

@SpringBootApplication
public class EurekaclientApplication {

	public static void main(String[] args) {
		SpringApplication.run(EurekaclientApplication.class, args);
	}

	@Component
	public class ShutdownHandler {

		private final ServiceInstanceRepository repository;
		private final EurekaClientService eurekaClientService;

		public ShutdownHandler(ServiceInstanceRepository repository, EurekaClientService eurekaClientService) {
			this.repository = repository;
			this.eurekaClientService = eurekaClientService;
		}

		@PreDestroy
		public void onShutdown() {
			repository.findAll().forEach(eurekaClientService::deregisterInstance);
		}
	}
}
