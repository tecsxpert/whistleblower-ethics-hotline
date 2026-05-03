package com.internship.tool.service;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import com.internship.tool.repository.ComplaintRepository;
import java.time.ZoneId;

@Service
@EnableScheduling
public class ScheduledTasks {

    @Autowired
    private EmailService emailService;

    @Autowired
    private ComplaintRepository complaintRepository;

    /**
     * Daily reminder - runs at 9:00 AM every day
     * Sends reminder emails to all users about pending complaints
     */
    @Scheduled(cron = "0 0 9 * * *")
    public void sendDailyReminder() {
        System.out.println("🔔 [SCHEDULED] Running daily reminder task...");
        
        try {
            // Count open complaints
            long openComplaintsCount = complaintRepository.findByStatus("OPEN").size();
            
            if (openComplaintsCount > 0) {
                // Send reminder to admin
                String adminEmail = "admin@whistleblower.com";
                emailService.sendDailyReminder(adminEmail, "Admin", (int) openComplaintsCount);
                System.out.println("✅ Daily reminder sent - " + openComplaintsCount + " open complaints");
            } else {
                System.out.println("ℹ️ No open complaints for daily reminder");
            }
        } catch (Exception e) {
            System.err.println("❌ Error in daily reminder task: " + e.getMessage());
            e.printStackTrace();
        }
    }

    /**
     * Deadline alert - runs every 6 hours
     * Checks for complaints approaching their deadlines
     */
    @Scheduled(cron = "0 0 */6 * * *")
    public void checkDeadlineAlerts() {
        System.out.println("⏰ [SCHEDULED] Running deadline alert task...");
        
        try {
            // Get all complaints in review status
            var inReviewComplaints = complaintRepository.findByStatus("IN_REVIEW");
            
            System.out.println("📊 Checking " + inReviewComplaints.size() + " complaints for deadline alerts");
            
            for (var complaint : inReviewComplaints) {
                // Check if complaint was created more than 5 days ago
                long createdTime = complaint.getCreatedAt().atZone(ZoneId.systemDefault()).toInstant().toEpochMilli();
                long currentTime = System.currentTimeMillis();
                long daysOld = (currentTime - createdTime) / (1000 * 60 * 60 * 24);
                
                if (daysOld >= 5) {
                    String daysRemaining = String.valueOf(7 - daysOld); // 7 day deadline
                    emailService.sendDeadlineAlert("admin@whistleblower.com", complaint.getTitle(), daysRemaining);
                    System.out.println("⚠️ Deadline alert sent for complaint: " + complaint.getTitle());
                }
            }
            
            System.out.println("✅ Deadline alert task completed");
        } catch (Exception e) {
            System.err.println("❌ Error in deadline alert task: " + e.getMessage());
            e.printStackTrace();
        }
    }

    /**
     * Hourly status check - for testing/monitoring
     * Can be enabled as needed
     */
    @Scheduled(cron = "0 0 * * * *")
    public void hourlyStatusCheck() {
        System.out.println("📈 [SCHEDULED] Hourly status check - Total complaints: " + complaintRepository.count());
    }
}
