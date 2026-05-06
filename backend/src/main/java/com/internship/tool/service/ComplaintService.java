package com.internship.tool.service;

import com.internship.tool.entity.Complaint;
import com.internship.tool.repository.ComplaintRepository;
import com.internship.tool.exception.ComplaintNotFoundException;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;


import java.time.LocalDateTime;
import java.util.List;

@Service
public class ComplaintService {

    private final ComplaintRepository repository;

    @Autowired
    private EmailService emailService;

    public ComplaintService(ComplaintRepository repository) {
        this.repository = repository;
    }

    // ✅ CREATE (clear cache) + Send email notification
    @CacheEvict(value = "complaints", allEntries = true)
    public Complaint createComplaint(Complaint complaint) {
        complaint.setStatus("OPEN");
        complaint.setCreatedAt(LocalDateTime.now());
        complaint.setUpdatedAt(LocalDateTime.now());
        Complaint saved = repository.save(complaint);
        
        // Send email notification
        try {
            emailService.sendComplaintCreatedEmail("admin@whistleblower.com", saved.getTitle(), saved.getId());
        } catch (Exception e) {
            System.err.println("⚠️ Failed to send complaint creation email: " + e.getMessage());
        }
        
        return saved;
    }

    // ✅ GET ALL (cached)
    @Cacheable(value = "complaints")
    public List<Complaint> getAllComplaints() {
        return repository.findAll();
    }

    // ✅ GET ALL PAGINATED (optional cache)
    @Cacheable(value = "complaintsPage", key = "#pageable.pageNumber")
    public Page<Complaint> getAllPaginated(Pageable pageable) {
        return repository.findAll(pageable);
    }

    // ✅ GET BY ID (cached)
    @Cacheable(value = "complaint", key = "#id")
    public Complaint getById(Long id) {
        return repository.findById(id)
                .orElseThrow(() ->
                        new ComplaintNotFoundException("Complaint not found with id " + id));
    }

    // ✅ UPDATE (clear cache) + Send status update email
    @CacheEvict(value = {"complaints", "complaint"}, allEntries = true)
    public Complaint updateComplaint(Long id, Complaint complaint) {
        Complaint existing = getById(id);
        String oldStatus = existing.getStatus();
        
        existing.setTitle(complaint.getTitle());
        existing.setDescription(complaint.getDescription());
        existing.setStatus(complaint.getStatus());
        existing.setUpdatedAt(LocalDateTime.now());
        Complaint updated = repository.save(existing);
        
        // Send status update email if status changed
        if (!oldStatus.equals(complaint.getStatus())) {
            try {
                emailService.sendComplaintStatusUpdateEmail("admin@whistleblower.com", updated.getTitle(), complaint.getStatus());
            } catch (Exception e) {
                System.err.println("⚠️ Failed to send status update email: " + e.getMessage());
            }
        }
        
        return updated;
    }

    // ✅ DELETE (clear cache)
    @CacheEvict(value = {"complaints", "complaint"}, allEntries = true)
    public void deleteComplaint(Long id) {
        if (!repository.existsById(id)) {
            throw new ComplaintNotFoundException("Complaint not found with id " + id);
        }
        repository.deleteById(id);
    }
}