package com.example.eurekaclient.services;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface ServiceInstanceRepository extends JpaRepository<ServiceInstance, Long> {

    ServiceInstance findByServiceNameAndHostNameAndHttpPort(String serviceName, String hostName, int httpPort);
}
