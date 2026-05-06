package com.internship.tool.service;

import com.internship.tool.entity.Complaint;
import com.internship.tool.exception.ComplaintNotFoundException;
import com.internship.tool.repository.ComplaintRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;

import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
@DisplayName("ComplaintService Unit Tests")
class ComplaintServiceTest {

    @Mock
    private ComplaintRepository complaintRepository;

    @InjectMocks
    private ComplaintService complaintService;

    private Complaint testComplaint;

    @BeforeEach
    void setUp() {
        testComplaint = new Complaint();
        testComplaint.setId(1L);
        testComplaint.setTitle("Test Complaint");
        testComplaint.setDescription("This is a test complaint");
        testComplaint.setStatus("OPEN");
        testComplaint.setCreatedAt(LocalDateTime.now());
        testComplaint.setUpdatedAt(LocalDateTime.now());
    }

    @Test
    @DisplayName("Should get all complaints")
    void testGetAllComplaints_Success() {
        // Arrange
        Complaint complaint1 = testComplaint;
        Complaint complaint2 = new Complaint(2L, "Complaint 2", "Description 2", "IN_REVIEW", 
                LocalDateTime.now(), LocalDateTime.now());
        List<Complaint> complaints = Arrays.asList(complaint1, complaint2);

        when(complaintRepository.findAll()).thenReturn(complaints);

        // Act
        List<Complaint> result = complaintService.getAllComplaints();

        // Assert
        assertNotNull(result);
        assertEquals(2, result.size());
        assertEquals("Test Complaint", result.get(0).getTitle());
        verify(complaintRepository, times(1)).findAll();
    }

    @Test
    @DisplayName("Should get paginated complaints")
    void testGetAllPaginated_Success() {
        // Arrange
        Pageable pageable = PageRequest.of(0, 5);
        Page<Complaint> complaintsPage = new PageImpl<>(Arrays.asList(testComplaint), pageable, 1);

        when(complaintRepository.findAll(pageable)).thenReturn(complaintsPage);

        // Act
        Page<Complaint> result = complaintService.getAllPaginated(pageable);

        // Assert
        assertNotNull(result);
        assertEquals(1, result.getTotalElements());
        assertEquals(1, result.getContent().size());
        verify(complaintRepository, times(1)).findAll(pageable);
    }

    @Test
    @DisplayName("Should get complaint by id successfully")
    void testGetById_Success() {
        // Arrange
        when(complaintRepository.findById(1L)).thenReturn(Optional.of(testComplaint));

        // Act
        Complaint result = complaintService.getById(1L);

        // Assert
        assertNotNull(result);
        assertEquals(1L, result.getId());
        assertEquals("Test Complaint", result.getTitle());
        verify(complaintRepository, times(1)).findById(1L);
    }

    @Test
    @DisplayName("Should throw exception when complaint not found")
    void testGetById_NotFound() {
        // Arrange
        when(complaintRepository.findById(999L)).thenReturn(Optional.empty());

        // Act & Assert
        assertThrows(ComplaintNotFoundException.class, () -> complaintService.getById(999L));
        verify(complaintRepository, times(1)).findById(999L);
    }
}
