async function loadAnalytics() {

    try {

        const response = await fetch("/api/analytics/data");

        const data = await response.json();

        console.log("Analytics Data:", data);


        // Pie Chart
        const pieCtx = document.getElementById("pieChart");

        if (pieCtx) {
            new Chart(pieCtx, {
                type: "doughnut",
                data: {
                    labels: ["Present", "Absent"],
                    datasets: [{
                        data: [
                            data.pie.present,
                            data.pie.absent
                        ]
                    }]
                }
            });
        }


        // Student Attendance Bar Chart

        const barCtx = document.getElementById("barChart");

        if (barCtx) {

            new Chart(barCtx, {

                type: "bar",

                data: {

                    labels: data.student_wise.map(
                        s => s.name
                    ),

                    datasets: [{
                        label: "Attendance %",
                        data: data.student_wise.map(
                            s => s.percentage
                        )
                    }]
                },

                options:{
                    responsive:true
                }

            });

        }



        // Daily Trend

        const dailyCtx =
            document.getElementById("dailyChart");


        if(dailyCtx){

            new Chart(dailyCtx,{

                type:"line",

                data:{

                    labels:data.daily_trend.map(
                        d=>d.date
                    ),

                    datasets:[{

                        label:"Present",

                        data:data.daily_trend.map(
                            d=>d.present
                        )

                    }]
                }

            });

        }



        // Monthly Trend

        const monthlyCtx =
            document.getElementById("monthlyChart");


        if(monthlyCtx){

            new Chart(monthlyCtx,{

                type:"line",

                data:{

                    labels:data.monthly_trend.map(
                        m=>m.month
                    ),

                    datasets:[{

                        label:"Attendance",

                        data:data.monthly_trend.map(
                            m=>m.present
                        )

                    }]
                }

            });

        }


    }

    catch(error){

        console.error(
            "Chart loading error:",
            error
        );

    }

}


document.addEventListener(
    "DOMContentLoaded",
    loadAnalytics
);