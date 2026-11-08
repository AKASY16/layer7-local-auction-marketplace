package com.layer7.marketplace.product.domain;

import com.layer7.marketplace.global.time.BaseTimeEntity;
import com.layer7.marketplace.user.domain.User;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "image_uploads")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class ImageUpload extends BaseTimeEntity {

	@Id
	@GeneratedValue(strategy = GenerationType.IDENTITY)
	private Long id;

	@ManyToOne(fetch = FetchType.LAZY, optional = false)
	@JoinColumn(name = "user_id", nullable = false)
	private User user;

	@Column(name = "object_key", nullable = false, unique = true, length = 512)
	private String objectKey;

	@Column(name = "content_type", nullable = false, length = 50)
	private String contentType;

	@Column(name = "size", nullable = false)
	private long size;

	@Enumerated(EnumType.STRING)
	@Column(name = "status", nullable = false, length = 20)
	private ImageUploadStatus status;

	public static ImageUpload create(User user, String objectKey, String contentType, long size) {
		ImageUpload upload = new ImageUpload();
		upload.user = user;
		upload.objectKey = objectKey;
		upload.contentType = contentType;
		upload.size = size;
		upload.status = ImageUploadStatus.PENDING;
		return upload;
	}
}
