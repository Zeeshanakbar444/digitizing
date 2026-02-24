$(document).ready(function () {
    $("#id_height").attr("min", "4").on('input', function() {
        if (parseInt($(this).val()) < 4) {
            $(this).val(4); // Reset to min value if below
        }
    });
    
    const maritalStatusField = $('#id_Marital_status');
    const Gender = $('#id_Gender');
    const kidsFieldWrapper = $('.form-row .field-kids');  // The field wrapper
    const kidsFieldWrapperForReg = $('.kids_list');  // The field wrapper
    const incomeFieldWrapper = $('.form-row.field-Require_income_From.field-Require_income_To');  // The field wrapper
    const incomeFieldWrapperForReg = $('.required_income');  // The field wrapper
    let income_from = $("#id_Require_income_From").val();  // The field wrapper
    let income_to = $("#id_Require_income_To").val();  // The field wrapper
    $('#id_Require_income_From').keyup(function(){
        var my_val = $(this).val()
        $(this).attr('value' , my_val)
        income_from = my_val
    });  // The field wrapper
    $('#id_Require_income_To').keyup(function(){
        var my_val = $(this).val()
        $(this).attr('value' , my_val)
        income_to = my_val
    });  // The field wrapper
    
    function toggleKidsField() {
        if (maritalStatusField.val() === 'Single') {
            kidsFieldWrapper.hide();
            kidsFieldWrapperForReg.hide();
            
        } else {
            kidsFieldWrapper.show();
            kidsFieldWrapperForReg.show();
        }
    }
    function toggleincomeField() {
        if (Gender.val() === 'Male') {
            $("#id_Require_income_From").attr('value' , 0)
            $("#id_Require_income_To").attr('value' , 0)
            incomeFieldWrapper.hide();
            incomeFieldWrapperForReg.hide();
        } else {
            $("#id_Require_income_From").attr('value' , income_from)
            $("#id_Require_income_To").attr('value' , income_to)
            incomeFieldWrapper.show();
            incomeFieldWrapperForReg.show();
        }
    }
    // Initial check when the page loads
    
    toggleKidsField();
    toggleincomeField();
    
    // Add event listener for changes
    maritalStatusField.on('change', toggleKidsField);
    Gender.on('change', toggleincomeField);
    // Gender.on('change', toggleincomeField);
});