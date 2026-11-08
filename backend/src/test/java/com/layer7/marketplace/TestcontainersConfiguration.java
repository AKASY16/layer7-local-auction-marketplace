package com.layer7.marketplace;

import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.beans.factory.InitializingBean;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.context.annotation.Bean;
import org.springframework.test.context.DynamicPropertyRegistrar;
import org.testcontainers.containers.GenericContainer;
import org.testcontainers.containers.wait.strategy.Wait;
import org.testcontainers.mysql.MySQLContainer;
import org.testcontainers.utility.DockerImageName;
import org.testcontainers.utility.MountableFile;
import software.amazon.awssdk.services.s3.S3Client;

// 도메인 패키지의 통합 테스트도 쓸 수 있도록 public으로 둔다 (support.IntegrationTest)
@TestConfiguration(proxyBeanMethods = false)
public class TestcontainersConfiguration {

	@Bean
	InitializingBean storageBucketInitializer(S3Client storage) {
		return () -> storage.createBucket(request -> request.bucket("product-images"));
	}

	@Bean(destroyMethod = "stop")
	GenericContainer<?> storageContainer() {
		GenericContainer<?> storage = new GenericContainer<>(DockerImageName.parse("chrislusf/seaweedfs:4.48"))
			.withExposedPorts(8333)
			.withCopyFileToContainer(MountableFile.forClasspathResource("storage/s3.json"), "/etc/s3.json")
			.withCommand("server", "-s3", "-s3.config=/etc/s3.json", "-master.volumeSizeLimitMB=1024")
			.waitingFor(Wait.forListeningPorts(8333));
		storage.start();
		return storage;
	}

	@Bean
	DynamicPropertyRegistrar storageProperties(GenericContainer<?> storageContainer) {
		String endpoint = "http://" + storageContainer.getHost() + ":" + storageContainer.getMappedPort(8333);
		return registry -> {
			registry.add("auction.storage.endpoint", () -> endpoint);
			registry.add("auction.storage.public-url", () -> endpoint + "/product-images");
		};
	}

	@Bean
	@ServiceConnection
	MySQLContainer mysqlContainer() {
		return new MySQLContainer(DockerImageName.parse("mysql:8.4"));
	}

}
