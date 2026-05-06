package com.internship.tool.config;

import com.internship.tool.entity.Complaint;
import com.internship.tool.repository.ComplaintRepository;
import org.springframework.boot.CommandLineRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class DataSeeder {

    @Bean
    public CommandLineRunner seedData(ComplaintRepository repository) {
        return args -> {

            // Only insert if database is empty
            if (repository.count() == 0) {

                for (int i = 1; i <= 30; i++) {
                    Complaint complaint = new Complaint();

                    complaint.setTitle("Sample Complaint " + i);
                    complaint.setDescription("This is test complaint number " + i);
                    complaint.setStatus("OPEN");

                    repository.save(complaint);
                }

                System.out.println("30 complaints inserted successfully");
            }
        };
    }
}