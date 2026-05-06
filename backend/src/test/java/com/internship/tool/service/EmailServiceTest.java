package com.internship.tool.service;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.thymeleaf.TemplateEngine;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
@DisplayName("EmailService Unit Tests")
class EmailServiceTest {

    @Mock
    private JavaMailSender javaMailSender;

    @Mock
    private TemplateEngine templateEngine;

    @InjectMocks
    private EmailService emailService;

    @Test
    @DisplayName("Should send simple email successfully")
    void testSendSimpleEmail_Success() {
        // Act
        emailService.sendSimpleEmail("test@example.com", "Test Subject", "Test body");

        // Assert
        verify(javaMailSender, times(1)).send(any(SimpleMailMessage.class));
    }

    @Test
    @DisplayName("Should handle email sending error gracefully")
    void testSendSimpleEmail_Error() {
        // Arrange
        doThrow(new RuntimeException("Mail server error")).when(javaMailSender).send(any(SimpleMailMessage.class));

        // Act & Assert - should not throw exception
        assertDoesNotThrow(() -> emailService.sendSimpleEmail("test@example.com", "Test", "Body"));
    }
}
