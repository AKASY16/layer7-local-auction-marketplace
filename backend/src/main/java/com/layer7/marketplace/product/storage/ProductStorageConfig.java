package com.layer7.marketplace.product.storage;

import java.net.URI;
import java.time.Duration;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import software.amazon.awssdk.auth.credentials.AwsBasicCredentials;
import software.amazon.awssdk.auth.credentials.StaticCredentialsProvider;
import software.amazon.awssdk.http.urlconnection.UrlConnectionHttpClient;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.S3Configuration;
import software.amazon.awssdk.services.s3.presigner.S3Presigner;

@Configuration
public class ProductStorageConfig {

	@Bean
	StaticCredentialsProvider storageCredentials(
		@Value("${auction.storage.access-key}") String accessKey,
		@Value("${auction.storage.secret-key}") String secretKey
	) {
		return StaticCredentialsProvider.create(AwsBasicCredentials.create(accessKey, secretKey));
	}

	@Bean
	S3Client productStorageClient(
		StaticCredentialsProvider credentials,
		@Value("${auction.storage.endpoint}") URI endpoint,
		@Value("${auction.storage.region}") String region
	) {
		return S3Client.builder()
			.endpointOverride(endpoint)
			.region(Region.of(region))
			.credentialsProvider(credentials)
			.forcePathStyle(true)
			.httpClientBuilder(UrlConnectionHttpClient.builder()
				.connectionTimeout(Duration.ofSeconds(3)).socketTimeout(Duration.ofSeconds(3)))
			.overrideConfiguration(config -> config.apiCallTimeout(Duration.ofSeconds(5)))
			.build();
	}

	@Bean
	S3Presigner productImagePresigner(
		StaticCredentialsProvider credentials,
		@Value("${auction.storage.endpoint}") URI endpoint,
		@Value("${auction.storage.region}") String region
	) {
		return S3Presigner.builder()
			.endpointOverride(endpoint)
			.region(Region.of(region))
			.credentialsProvider(credentials)
			.serviceConfiguration(S3Configuration.builder()
				.pathStyleAccessEnabled(true).checksumValidationEnabled(false).build())
			.build();
	}
}
