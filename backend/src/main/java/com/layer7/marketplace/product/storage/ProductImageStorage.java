package com.layer7.marketplace.product.storage;

import com.layer7.marketplace.global.error.BusinessException;
import com.layer7.marketplace.global.error.ErrorCode;
import java.time.Duration;
import java.time.Instant;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.HeadObjectResponse;
import software.amazon.awssdk.services.s3.model.S3Exception;
import software.amazon.awssdk.services.s3.presigner.S3Presigner;
import software.amazon.awssdk.services.s3.presigner.model.PresignedPutObjectRequest;

@Component
public class ProductImageStorage {

	private final S3Client client;
	private final S3Presigner presigner;
	private final String bucket;
	private final String publicUrl;

	public ProductImageStorage(S3Client client, S3Presigner presigner,
		@Value("${auction.storage.bucket}") String bucket,
		@Value("${auction.storage.public-url}") String publicUrl) {
		this.client = client;
		this.presigner = presigner;
		this.bucket = bucket;
		this.publicUrl = publicUrl.replaceAll("/+$", "");
	}

	public UploadUrl issueUploadUrl(String objectKey, String contentType) {
		PresignedPutObjectRequest signed = presigner.presignPutObject(request -> request
			.signatureDuration(Duration.ofMinutes(10))
			.putObjectRequest(put -> put.bucket(bucket).key(objectKey).contentType(contentType)));
		return new UploadUrl(objectKey, signed.url().toString(), signed.expiration(),
			Map.of("Content-Type", contentType));
	}

	public void verifyObject(String objectKey, String contentType, long size) {
		HeadObjectResponse object;
		try {
			object = client.headObject(request -> request.bucket(bucket).key(objectKey));
		} catch (S3Exception exception) {
			if (exception.statusCode() == 404) {
				throw new BusinessException(ErrorCode.INVALID_UPLOAD);
			}
			throw exception;
		}
		if (object.contentLength() != size || !contentType.equals(object.contentType())) {
			throw new BusinessException(ErrorCode.INVALID_UPLOAD);
		}
	}

	public String getPublicUrl(String objectKey) {
		// objectKey는 서버가 만든 uploads/{uuid}만 저장한다.
		return publicUrl + "/" + objectKey;
	}

	public record UploadUrl(String objectKey, String uploadUrl, Instant expiresAt, Map<String, String> headers) {
	}
}
