package com.internship.tool.service;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.mail.javamail.MimeMessageHelper;
import org.springframework.stereotype.Service;
import org.thymeleaf.TemplateEngine;
import org.thymeleaf.context.Context;

import jakarta.mail.MessagingException;
import jakarta.mail.internet.MimeMessage;
import java.util.Map;

@Service
public class EmailService {

    @Autowired
    private JavaMailSender mailSender;

    @Autowired
    private TemplateEngine templateEngine;

    /**
     * Send simple text email
     */
    public void sendSimpleEmail(String to, String subject, String body) {
        try {
            SimpleMailMessage message = new SimpleMailMessage();
            message.setFrom("noreply@whistleblower.com");
            message.setTo(to);
            message.setSubject(subject);
            message.setText(body);
            mailSender.send(message);
            System.out.println("✅ Email sent to: " + to);
        } catch (Exception e) {
            System.err.println("❌ Error sending email: " + e.getMessage());
            e.printStackTrace();
        }
    }

    /**
     * Send HTML email using Thymeleaf template
     */
    public void sendTemplateEmail(String to, String subject, String templateName, Map<String, Object> variables) {
    try {
        System.out.println("📧 Preparing email...");

        MimeMessage mimeMessage = mailSender.createMimeMessage();
        MimeMessageHelper helper = new MimeMessageHelper(mimeMessage, true, "UTF-8");

        Context context = new Context();
        if (variables != null) {
            context.setVariables(variables);
        }

        String htmlContent = templateEngine.process(templateName, context);

        helper.setFrom("noreply@whistleblower.com");
        helper.setTo(to);
        helper.setSubject(subject);
        helper.setText(htmlContent, true);

        mailSender.send(mimeMessage);

        System.out.println("✅ Email sent successfully");

    } catch (Exception e) {
        System.err.println("❌ Email FAILED but API will continue");
        e.printStackTrace();   // VERY IMPORTANT
    }
}

    /**
     * Send complaint creation notification email
     */
    public void sendComplaintCreatedEmail(String to, String complaintTitle, Long complaintId) {
        Map<String, Object> variables = Map.of(
                "title", complaintTitle,
                "complaintId", complaintId,
                "timestamp", System.currentTimeMillis()
        );
        sendTemplateEmail(to, "New Complaint Created", "complaint-created", variables);
    }

    /**
     * Send daily reminder email
     */
    public void sendDailyReminder(String to, String userName, int pendingComplaints) {
        Map<String, Object> variables = Map.of(
                "name", userName,
                "pendingCount", pendingComplaints,
                "date", new java.util.Date()
        );
        sendTemplateEmail(to, "Daily Complaint Reminder", "daily-reminder", variables);
    }

    /**
     * Send deadline alert email
     */
    public void sendDeadlineAlert(String to, String complaintTitle, String daysRemaining) {
        Map<String, Object> variables = Map.of(
                "title", complaintTitle,
                "daysRemaining", daysRemaining,
                "date", new java.util.Date()
        );
        sendTemplateEmail(to, "Deadline Alert", "deadline-alert", variables);
    }

    /**
     * Send complaint status update email
     */
    public void sendComplaintStatusUpdateEmail(String to, String complaintTitle, String newStatus) {
        Map<String, Object> variables = Map.of(
                "title", complaintTitle,
                "status", newStatus,
                "timestamp", System.currentTimeMillis()
        );
        sendTemplateEmail(to, "Complaint Status Updated", "status-update", variables);
    }
}
